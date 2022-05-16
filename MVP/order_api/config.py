"""
--gb.ru/lessons/219762/homework
--mmankova

"""
from pydantic import Field
from datetime import date
from dwh_lib import dmc_config, DmcConfig

class InsApiConfig(DmcConfig):

    MAX_PERIOD_LENGTH: int = Field(0, env='MAX_PERIOD_LENGTH')
    """ Maximum request period length in days """

    MAX_VINS: int = Field(1000, env='MAX_VINS')
    """ Maximum number of VINS in request """

    MIN_PERIOD: date = Field(date(2019, 1, 1), env='MIN_PERIOD')
    """ Minimum request period date """

dmc_config.config_class = InsApiConfig
