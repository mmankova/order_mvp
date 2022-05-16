"""
--gb.ru/lessons/219762/homework
--mmankova

"""

create table StatusDict
(
    status_id int8 NOT NULL,
    status_name varchar(256) NOT NULL,
    CONSTRAINT StatusDict_pkey PRIMARY KEY (status_id),
	CONSTRAINT StatusDict_uq UNIQUE (status_name)
);
    COMMENT ON TABLE StatusDict IS 'Справочник статусов заказа';
    COMMENT ON COLUMN StatusDict.status_id IS 'id  статуса';
    COMMENT ON COLUMN StatusDict.status_name IS 'Наименование статуса';

create table Client
(
    client_id  int8 NOT NULL, --id клиента
    name  varchar(256)  NOT NULL, -- Наименование
    adress  varchar(256) NULL, -- адрес
    CONSTRAINT Client_pkey PRIMARY KEY (client_id)
);
    COMMENT ON TABLE Client IS 'Клиенты';
    COMMENT ON COLUMN Client.client_id IS 'id клиента';
    COMMENT ON COLUMN Client.name IS 'Наименование клиента';
    COMMENT ON COLUMN Client.adress IS 'адрес клиента';

create table Restaurant
(
    restaurant_id  int8 NOT NULL, --id  ресторана
    name  varchar(256)  NOT NULL, -- Наименование
    rating  varchar(256) NULL, -- рейтинг
    CONSTRAINT Restaurant_pkey PRIMARY KEY (restaurant_id)
);
    COMMENT ON TABLE Restaurant IS 'Ресторан';
    COMMENT ON COLUMN Restaurant.restaurant_id IS 'id  ресторана';
    COMMENT ON COLUMN Restaurant.name IS 'Наименование ресторана';
    COMMENT ON COLUMN Restaurant.rating IS 'рейтинг ресторана';

create table Delivery
(
    delivery_id  int8 NOT NULL, --id доставщика
    name  varchar(256)  NOT NULL, -- Наименование
    rating  varchar(256) NULL, -- рейтинг
    CONSTRAINT Delivery_pkey PRIMARY KEY (delivery_id)
);
    COMMENT ON TABLE  Delivery IS 'Доставщики';
    COMMENT ON COLUMN Delivery.delivery_id IS 'id  доставщика';
    COMMENT ON COLUMN Delivery.name IS 'Наименование доставщика';
    COMMENT ON COLUMN Delivery.rating IS 'рейтинг доставщика';

create table Order
(
    order_id int8 NOT NULL, --id заказа
    name varchar(256)  NOT NULL, -- Наименование 
    creation_time  timestamptz NOT NULL, -- Время созания 
    modification_time timestamptz NOT NULL, -- Время изменения 
    status_id int8 NOT NULL, --статус заказа
    payment_method varchar(256) NULL, -- способ оплаты
    rating int8 NULL, --оценка 
	client_id  int8 NULL, --клиент заказа
    restaurant_id  int8 NOT, --ресторан 
    delivery_id  int8 NOT , --доставщик
    CONSTRAINT Order_fk_StatusDict FOREIGN KEY (status_id) REFERENCES StatusDict(status_id) ON DELETE CASCADE,
    CONSTRAINT Order_pkey PRIMARY KEY (order_id),
    CONSTRAINT Order_fk_Client FOREIGN KEY (client_id) REFERENCES Client(client_id) ON DELETE CASCADE,
    CONSTRAINT Order_fk_Restaurant FOREIGN KEY (restaurant_id) REFERENCES Restaurant(restaurant_id) ON DELETE CASCADE,
    CONSTRAINT Order_fk_Delivery FOREIGN KEY (delivery_id) REFERENCES Delivery(delivery_id) ON DELETE CASCADE
    );
COMMENT ON TABLE Order IS 'Заказы';

COMMENT ON COLUMN  Order.order_id IS 'id заказа';
COMMENT ON COLUMN  Order.name IS 'Наименование  заказа';
COMMENT ON COLUMN  Order.creation_time IS 'Время создания заказа';
COMMENT ON COLUMN  Order.modification_time IS 'Время изменения  заказа';
COMMENT ON COLUMN  Order.status_id IS 'статус заказа';
COMMENT ON COLUMN  Order.payment_method IS 'способ оплаты';
COMMENT ON COLUMN  Order.rating IS 'оценка ';
COMMENT ON COLUMN  Order.client_id IS 'клиент заказа';
COMMENT ON COLUMN  Order.restaurant_id IS 'ресторан ';
COMMENT ON COLUMN  Order.delivery_id   IS 'доставщик';


