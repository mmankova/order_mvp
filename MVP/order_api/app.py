"""
--gb.ru/lessons/219762/homework
--mmankova
"""
import aioredis
from hashlib import md5
from loguru import logger
from datetime import date, datetime
from fastapi import FastAPI, Header, Response, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from config import *
from dwh_lib import dmc_config, localnow, datetime_tolocal, call_stats_async, template_async
from dmc_ins_lib import (
    Client, ClientRegistrar, Subscription, SubscriptionVIN, Vehicle, Request
)

from model.Order import AuthResponse
from model.vehicle import VehicleRegisterRequest, VehicleInfoResponse, VehicleInfoResponsePayload
from model.incident import Incident, IncidentsResponsePayload, IncidentsResponse

# Mail address for API subscriptions
API_MAIL = 'api@dwh.iconsoft.ru'

# Stats root key
STATS_ROOT = 'stats-api-ins'

# Get a client_id using auth header
async def get_client_id(credentials: HTTPBasicCredentials) -> int:
    if not credentials.username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail='username not provided')
    try:
        return int(credentials.username)
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='client_id must be used for username')

# Get a client object and verify its password
async def check_client(credentials: HTTPBasicCredentials, session: AsyncSession) -> Client:
    client_id = await get_client_id(credentials)
    stmt = select(Client).where(Client.client_id == client_id)
    if not (client := (await session.execute(stmt)).scalar()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Client {client_id} does not exist')

    logger.debug(f'Client {client.client_id}:{client.client_name} found')

    if (client.passw and client.passw == md5(credentials.password.encode('utf-8')).hexdigest()) or \
       (not client.passw and not credentials.password):
        return client
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='invalid password')

def make_request(client, rq_type='api_subscribe', state='success', vins_count=1):
    rq = Request()
    rq.client_id = client.client_id
    rq.email = API_MAIL
    rq.email_person = 'DWH API Request'
    rq.mail_id = API_MAIL
    rq.rq_type = rq_type
    rq.rq_ts = localnow()
    rq.vins_count = vins_count
    rq.state = state
    rq.started = localnow()
    rq.closed = localnow()
    return rq

# Global objects
app = FastAPI()
security = HTTPBasic()
engine = None

# App init
@app.on_event('startup')
async def startup_event():
    global engine

    dmc_config.config.enable_std_log()
    assert dmc_config.config.DB_URL, 'DB_URL not set'
    assert dmc_config.config.REDIS_URL, 'REDIS_URL not set'
    assert 'postgresql+asyncpg://' in dmc_config.config.DB_URL, 'postgresql+asynpg connection expected'

    logger.info(f'Using DB_URL {dmc_config.config.DB_URL}')
    engine = create_async_engine(dmc_config.config.DB_URL, pool_size=dmc_config.config.DB_POOL_SIZE, echo=False)

    logger.info(f'Using REDIS_URL {dmc_config.config.REDIS_URL}')
    _ = aioredis.from_url(dmc_config.config.REDIS_URL)

    async with call_stats_async(STATS_ROOT) as stats:
        await stats.start()

# Server status
@app.get('/api/ins/v1/server/status')
async def healthCheck():
    """ Server status """
    async with AsyncSession(engine) as session, \
        call_stats_async(STATS_ROOT) as stats:

        await session.scalar(select(1))

    return JSONResponse(await stats.get_stats())

# Auth API
# TODO: proper authorization with tokens
@app.post('/api/ins/v1/token', response_model=AuthResponse)
async def authenticationRequest(
    grant_type: str = None, 
    scope: str = None, 
    сlient_assertion_type: str = None, 
    client_assertion: str = None,
    credentials: HTTPBasicCredentials = Depends(security)):
    """ Получение JW-токена доступа (эмулятор) """

    async with AsyncSession(engine) as session, \
        call_stats_async(STATS_ROOT):

        # Get the client
        client = await check_client(credentials, session)

        # Get token from registrar
        redis = aioredis.from_url(dmc_config.config.REDIS_URL)
        reg = await ClientRegistrar.from_redis_async(redis)
        token = reg.register(client.client_id)
        await reg.to_redis_async(redis)

        # Thats all
        return AuthResponse(access_token=token, scope=scope or 'vehicles', refresh_token=token)

# Vehicle incidents API
@app.get('/api/ins/v1/vehicles/incidents/{vehicleId}', response_model=IncidentsResponse)
async def getVehicleIncidents(
    response: Response,
    vehicleId: str,
    page: int = None,
    fromDateTime: datetime = None,
    toDateTime: datetime = None,
    x_fapi_interaction_id: str = Header(None),
    x_idempotency_key: str = Header(None),
    x_jws_signature: str = Header(None),
    credentials: HTTPBasicCredentials = Depends(security)):
    """ Запрос информации по списку инцидентов транспортного средства за период """

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session, \
        session.begin(), \
        template_async('get_incidents_by_vin.sql') as template, \
        call_stats_async(STATS_ROOT):

        # Get the client
        client = await check_client(credentials, session)

        # Get the incidents
        logger.info(f'Loading incidents for {client.client_id} VIN {vehicleId} for [{fromDateTime}, {toDateTime}]')
        sql = template.render(
            client_id=client.client_id,
            vin=vehicleId,
            p_from=fromDateTime or dmc_config.config.MIN_PERIOD,
            p_to=toDateTime or datetime(2099, 12, 31)
        )
        pg_data = await session.execute(sql)
        obj_data = [Incident.from_dbrow(r) for r in pg_data.mappings()]
        logger.info(f'{len(obj_data)} records found')

        # Make a request
        rq = make_request(client, rq_type='api_request', vins_count=len(obj_data))
        session.add(rq)

        response.headers['x-fapi-interaction-id'] = x_fapi_interaction_id or ''
        response.headers['x-jws-signature'] = x_jws_signature or ''
        response.status_code = status.HTTP_200_OK
        return IncidentsResponse(Data=IncidentsResponsePayload(Incident=obj_data))

# Incidents API
@app.get('/api/ins/v1/vehicles/incidents', response_model=IncidentsResponse)
async def getIncidents(
    response: Response,
    page: int = None,
    fromDateTime: datetime = None,
    toDateTime: datetime = None,
    x_fapi_interaction_id: str = Header(None),
    x_idempotency_key: str = Header(None),
    x_jws_signature: str = Header(None),
    credentials: HTTPBasicCredentials = Depends(security)):
    """ Запрос информации по списку инцидентов всех транспортных средства за период """

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session, \
        session.begin(), \
        template_async('get_incidents_by_client.sql') as template, \
        call_stats_async(STATS_ROOT):

        # Get the client
        client = await check_client(credentials, session)

        # Get the incidents
        logger.info(f'Loading incidents for {client.client_id} subscriptions for [{fromDateTime}, {toDateTime}]')
        sql = template.render(
            client_id=client.client_id,
            p_from=fromDateTime or dmc_config.config.MIN_PERIOD,
            p_to=toDateTime or datetime(2099, 12, 31)
        )
        pg_data = await session.execute(sql)
        obj_data = [Incident.from_dbrow(r) for r in pg_data.mappings()]
        logger.info(f'{len(obj_data)} records found')

        # Make a request
        rq = make_request(client, rq_type='api_request', vins_count=len(obj_data))
        session.add(rq)

        # Make response
        response.headers['x-fapi-interaction-id'] = x_fapi_interaction_id or ''
        response.headers['x-jws-signature'] = x_jws_signature or ''
        response.status_code = status.HTTP_200_OK
        return IncidentsResponse(Data=IncidentsResponsePayload(Incident=obj_data))

# Vehicle registration API
@app.post('/api/ins/v1/vehicles', response_model=VehicleInfoResponse)
async def registerVehicle(
    response: Response,
    request: VehicleRegisterRequest,
    x_fapi_interaction_id: str = Header(None),
    x_idempotency_key: str = Header(None),
    x_jws_signature: str = Header(None),
    credentials: HTTPBasicCredentials = Depends(security)):
    """ Привязка транспортного средства к СК """

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session, \
        session.begin(), \
        call_stats_async(STATS_ROOT):

        # Get the client
        client = await check_client(credentials, session)

        # Find a vehicle with given VIN
        stmt = select(Vehicle).where(Vehicle.vin == request.Data.VIN)
        if not (vehicle := (await session.execute(stmt)).scalar()):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                detail=f'Vehicle {request.Data.VIN} not found',
                                headers={'x-fapi-interaction-id': x_fapi_interaction_id or '',
                                         'x-jws-signature': x_jws_signature or ''})
        logger.debug(f'Vehicle {vehicle.vin} found')

        # Make a request
        # We need to flush transaction to get rq.rq_id
        rq = make_request(client, rq_type='api_subscribe')
        session.add(rq)
        await session.flush()

        # Find or make an API subscription
        stmt = select(Subscription).where(and_(Subscription.client_id == client.client_id, 
                                                Subscription.email == API_MAIL))
        if subs := (await session.execute(stmt)).scalar():
            logger.debug(f'API subscription {subs.subs_id} found')
            subs.rq_id = rq.rq_id
        else:
            subs = Subscription(
                client_id=client.client_id,
                rq_id=rq.rq_id,
                email=API_MAIL,
                subs_period=[localnow(), datetime_tolocal(datetime(2099, 12, 31, 23, 59, 59))],
                is_active=True,
                is_unlim=True)
            session.add(subs)
            logger.debug(f'API subscription {subs.subs_id} created for client {client.client_id}')

        # Save VIN to subscription
        if vehicle.vin in subs:
            # VIN already present, check if active
            sb_vin = subs[vehicle.vin]
            if sb_vin.is_active:
                logger.debug(f'VIN {vehicle.vin} already exists in API subscription {subs.subs_id}')
            else:
                sb_vin.is_active = True
                sb_vin.modified = localnow()
                logger.debug(f'VIN {vehicle.vin} reactivated in API subscription {subs.subs_id}')
        else:
            # Nope, create one
            sb_vin = SubscriptionVIN(subs_id=subs.subs_id, vin=vehicle.vin, is_active=True)
            subs.vins.append(sb_vin)
            logger.debug(f'VIN {vehicle.vin} added to API subscription {subs.subs_id}')

        # Make response
        response.headers['x-fapi-interaction-id'] = x_fapi_interaction_id or ''
        response.headers['x-jws-signature'] = x_jws_signature or ''
        response.status_code = status.HTTP_201_CREATED
        return VehicleInfoResponse(
            Data=VehicleInfoResponsePayload(
                vehicleId=vehicle.vin,
                creationDateTime=vehicle.creation_ts,
                VIN=vehicle.vin,
                status='deleted' if vehicle.is_utilized else 'accepted'))


# Vehicle registration status API
@app.get('/api/ins/v1/vehicles/{vehicleId}', response_model=VehicleInfoResponse)
async def getVehicle(
    response: Response,
    vehicleId: str,
    x_fapi_interaction_id: str = Header(None),
    x_idempotency_key: str = Header(None),
    x_jws_signature: str = Header(None),
    credentials: HTTPBasicCredentials = Depends(security)):
    """ Запрос статуса привязки транспортного средства к СК """

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session, \
        session.begin(), \
        call_stats_async(STATS_ROOT):

        # Get the client
        client = await check_client(credentials, session)

        # Find an API subscription
        stmt = select(Subscription).where(and_(Subscription.client_id == client.client_id, 
                                                Subscription.email == API_MAIL))
        if not (subs := (await session.execute(stmt)).scalar()) or vehicleId not in subs.vins_list:
            # Either API subscription not exist or VIN is not there
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                detail=f'Vehicle {vehicleId} not found in client {client.client_id} subscriptions',
                                headers={'x-fapi-interaction-id': x_fapi_interaction_id or '',
                                         'x-jws-signature': x_jws_signature or ''})

        # Load vehicle
        stmt = select(Vehicle).where(Vehicle.vin == vehicleId)
        if not (vehicle := (await session.execute(stmt)).scalar()):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                detail=f'Vehicle {vehicleId} not found',
                                headers={'x-fapi-interaction-id': x_fapi_interaction_id or '',
                                         'x-jws-signature': x_jws_signature or ''})
        logger.debug(f'Vehicle {vehicle.vin} found in subscription {subs.subs_id}')
    
        # Make response
        response.headers['x-fapi-interaction-id'] = x_fapi_interaction_id or ''
        response.headers['x-jws-signature'] = x_jws_signature or ''
        response.status_code = status.HTTP_200_OK
        return VehicleInfoResponse(
            Data=VehicleInfoResponsePayload(
                vehicleId=vehicle.vin,
                creationDateTime=vehicle.creation_ts,
                VIN=vehicle.vin,
                status='deleted' if vehicle.is_utilized else 'accepted'))


# Vehicle registration cancel API
@app.delete('/api/ins/v1/vehicles/{vehicleId}')
async def unregisterVehicle(
    vehicleId: str,
    x_fapi_interaction_id: str = Header(None),
    x_idempotency_key: str = Header(None),
    x_jws_signature: str = Header(None),
    credentials: HTTPBasicCredentials = Depends(security)):
    """ Отзыв регистрации отслеживания событий транспортного средства """

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session, \
        session.begin(), \
        call_stats_async(STATS_ROOT):

        # Get the client
        client = await check_client(credentials, session)

        # Find an API subscription
        stmt = select(Subscription).where(and_(Subscription.client_id == client.client_id, 
                                                Subscription.email == API_MAIL))
        if not (subs := (await session.execute(stmt)).scalar()) or vehicleId not in subs.vins_list:
            # Either API subscription not exists or VIN is not there
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                detail=f'Vehicle {vehicleId} not found in client {client.client_id} subscriptions',
                                headers={'x-fapi-interaction-id': x_fapi_interaction_id or '',
                                         'x-jws-signature': x_jws_signature or ''})
        else:
            # Mark VIN as inactive and save
            sb_vin = subs[vehicleId]
            sb_vin.is_active = False
            sb_vin.modified = localnow()

            # Make a request
            rq = make_request(client, rq_type='api_unsubscribe')
            session.add(rq)

            # Make response
            return Response(status_code=status.HTTP_204_NO_CONTENT, 
                            headers={'x-fapi-interaction-id': x_fapi_interaction_id or '',
                                     'x-jws-signature': x_jws_signature or ''})



# Exception handlers
# @app.exception_handler(AssertionError)
# async def assert_error_exception_handler(request, ex):
#     # await stats.update_stats(success=False)
#     # return Response(content=str(ex), status_code=status.HTTP_404_NOT_FOUND)
#     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))

# @app.exception_handler(Exception)
# async def exception_handler(request, ex):
#     try:
#         await stats.update_stats(success=False)
#     except:
#         pass
#     return Response(content=str(ex), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
