CREATE TABLE public.account_transactions (
  transaction_id integer NOT NULL DEFAULT nextval('account_transactions_transaction_id_seq'::regclass),
  account_id integer NOT NULL,
  transaction_type character varying NOT NULL,
  related_id integer,
  amount numeric NOT NULL,
  balance_after numeric NOT NULL,
  description text,
  transaction_date timestamp without time zone NOT NULL,
  created_by character varying NOT NULL,
  CONSTRAINT account_transactions_pkey PRIMARY KEY (transaction_id),
  CONSTRAINT account_transactions_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(account_id)
);
CREATE TABLE public.accounts (
  account_id integer NOT NULL DEFAULT nextval('accounts_account_id_seq'::regclass),
  store character varying NOT NULL,
  account_name character varying NOT NULL,
  account_type character varying NOT NULL CHECK (account_type::text = ANY (ARRAY['cash'::character varying, 'bank'::character varying]::text[])),
  bank_name character varying,
  account_number character varying,
  balance numeric NOT NULL DEFAULT 0.00,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  is_default boolean DEFAULT false,
  CONSTRAINT accounts_pkey PRIMARY KEY (account_id)
);
CREATE TABLE public.activity_log (
  logid integer NOT NULL DEFAULT nextval('activity_log_logid_seq'::regclass),
  user_id integer NOT NULL,
  activity text NOT NULL,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT activity_log_pkey PRIMARY KEY (logid),
  CONSTRAINT activity_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.debt (
  debtid integer NOT NULL DEFAULT nextval('debt_debtid_seq'::regclass),
  type character varying NOT NULL CHECK (type::text = ANY (ARRAY['supplier'::character varying::text, 'customer'::character varying::text])),
  relatedid integer NOT NULL,
  amount numeric NOT NULL,
  paid numeric DEFAULT 0,
  date timestamp without time zone,
  description text,
  store character varying,
  due_date timestamp without time zone,
  CONSTRAINT debt_pkey PRIMARY KEY (debtid)
);
CREATE TABLE public.operational_expense (
  expense_id integer NOT NULL DEFAULT nextval('operational_expense_expense_id_seq'::regclass),
  store character varying NOT NULL,
  expense_type character varying NOT NULL CHECK (expense_type::text = ANY (ARRAY['salary'::character varying, 'rent'::character varying, 'utility'::character varying, 'maintenance'::character varying, 'supplies'::character varying, 'transport'::character varying, 'other'::character varying]::text[])),
  amount numeric NOT NULL,
  description text,
  reference_id integer,
  expense_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  account_id integer,
  created_by character varying,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT operational_expense_pkey PRIMARY KEY (expense_id),
  CONSTRAINT operational_expense_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(account_id)
);
CREATE TABLE public.payment_history (
  paymentid integer NOT NULL DEFAULT nextval('payment_history_paymentid_seq'::regclass),
  debtid integer NOT NULL,
  paidamount numeric NOT NULL,
  paidat timestamp without time zone,
  description text,
  CONSTRAINT payment_history_pkey PRIMARY KEY (paymentid),
  CONSTRAINT payment_history_debtid_fkey FOREIGN KEY (debtid) REFERENCES public.debt(debtid)
);
CREATE TABLE public.pegawai (
  pegawai_id integer NOT NULL DEFAULT nextval('pegawai_pegawai_id_seq'::regclass),
  store character varying NOT NULL,
  nama character varying NOT NULL,
  posisi character varying,
  gaji_bulanan numeric NOT NULL DEFAULT 0,
  tanggal_pembayaran integer NOT NULL DEFAULT 1 CHECK (tanggal_pembayaran >= 1 AND tanggal_pembayaran <= 31),
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pegawai_pkey PRIMARY KEY (pegawai_id)
);
CREATE TABLE public.pegawai_payment (
  payment_id integer NOT NULL DEFAULT nextval('pegawai_payment_payment_id_seq'::regclass),
  pegawai_id integer NOT NULL,
  bulan date NOT NULL,
  jumlah numeric NOT NULL,
  paid_at timestamp without time zone,
  status character varying DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'paid'::character varying]::text[])),
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pegawai_payment_pkey PRIMARY KEY (payment_id),
  CONSTRAINT pegawai_payment_pegawai_id_fkey FOREIGN KEY (pegawai_id) REFERENCES public.pegawai(pegawai_id)
);
CREATE TABLE public.product (
  productid integer NOT NULL DEFAULT nextval('product_productid_seq'::regclass),
  store character varying NOT NULL,
  productname character varying NOT NULL,
  type character varying,
  color character varying,
  harga numeric,
  quantity integer DEFAULT 0,
  description text,
  updateat timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  size character varying,
  brand character varying,
  CONSTRAINT product_pkey PRIMARY KEY (productid)
);
CREATE TABLE public.product_warehouse (
  id integer NOT NULL DEFAULT nextval('product_warehouse_id_seq'::regclass),
  productid integer NOT NULL,
  warehouseid integer NOT NULL,
  quantity integer NOT NULL DEFAULT 0,
  CONSTRAINT product_warehouse_pkey PRIMARY KEY (id),
  CONSTRAINT product_warehouse_productid_fkey FOREIGN KEY (productid) REFERENCES public.product(productid),
  CONSTRAINT product_warehouse_warehouseid_fkey FOREIGN KEY (warehouseid) REFERENCES public.warehouse_list(warehouseid)
);
CREATE TABLE public.productsupply (
  supplyid integer NOT NULL DEFAULT nextval('productsupply_supplyid_seq'::regclass),
  productid integer NOT NULL,
  supplierid integer NOT NULL,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  date timestamp without time zone,
  CONSTRAINT productsupply_pkey PRIMARY KEY (supplyid),
  CONSTRAINT productsupply_productid_fkey FOREIGN KEY (productid) REFERENCES public.product(productid),
  CONSTRAINT productsupply_supplierid_fkey FOREIGN KEY (supplierid) REFERENCES public.supplier(supplierid)
);
CREATE TABLE public.purchase (
  purchaseid integer NOT NULL DEFAULT nextval('purchase_purchaseid_seq'::regclass),
  productid integer NOT NULL,
  supplierid integer NOT NULL,
  warehouseid integer NOT NULL,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  total numeric DEFAULT ((quantity)::numeric * price),
  payment_type character varying NOT NULL CHECK (payment_type::text = ANY (ARRAY['cash'::character varying::text, 'credit'::character varying::text])),
  description text,
  date timestamp without time zone,
  CONSTRAINT purchase_pkey PRIMARY KEY (purchaseid),
  CONSTRAINT purchase_productid_fkey FOREIGN KEY (productid) REFERENCES public.product(productid),
  CONSTRAINT purchase_supplierid_fkey FOREIGN KEY (supplierid) REFERENCES public.supplier(supplierid),
  CONSTRAINT purchase_warehouseid_fkey FOREIGN KEY (warehouseid) REFERENCES public.warehouse_list(warehouseid)
);
CREATE TABLE public.purchase_return (
  return_id integer NOT NULL DEFAULT nextval('purchase_return_return_id_seq'::regclass),
  store character varying NOT NULL,
  supplier_id integer NOT NULL,
  warehouse_id integer NOT NULL,
  total_amount numeric NOT NULL DEFAULT 0,
  return_type character varying NOT NULL CHECK (return_type::text = ANY (ARRAY['refund'::character varying, 'replacement'::character varying, 'credit_note'::character varying]::text[])),
  status character varying NOT NULL DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'approved'::character varying, 'completed'::character varying, 'rejected'::character varying]::text[])),
  reason text,
  description text,
  account_id integer,
  return_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by character varying,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT purchase_return_pkey PRIMARY KEY (return_id),
  CONSTRAINT purchase_return_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(supplierid),
  CONSTRAINT purchase_return_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouse_list(warehouseid),
  CONSTRAINT purchase_return_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(account_id)
);
CREATE TABLE public.purchase_return_items (
  item_id integer NOT NULL DEFAULT nextval('purchase_return_items_item_id_seq'::regclass),
  return_id integer NOT NULL,
  product_id integer NOT NULL,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  subtotal numeric DEFAULT ((quantity)::numeric * price),
  CONSTRAINT purchase_return_items_pkey PRIMARY KEY (item_id),
  CONSTRAINT purchase_return_items_return_id_fkey FOREIGN KEY (return_id) REFERENCES public.purchase_return(return_id),
  CONSTRAINT purchase_return_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(productid)
);
CREATE TABLE public.purchase_transaction (
  transaction_id integer NOT NULL DEFAULT nextval('purchase_transaction_transaction_id_seq'::regclass),
  store character varying NOT NULL,
  supplier_id integer NOT NULL,
  warehouse_id integer NOT NULL,
  total_amount numeric NOT NULL DEFAULT 0,
  payment_type character varying NOT NULL CHECK (payment_type::text = ANY (ARRAY['cash'::character varying, 'credit'::character varying]::text[])),
  due_date timestamp without time zone,
  account_id integer,
  description text,
  transaction_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by character varying,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT purchase_transaction_pkey PRIMARY KEY (transaction_id),
  CONSTRAINT purchase_transaction_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.supplier(supplierid),
  CONSTRAINT purchase_transaction_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouse_list(warehouseid),
  CONSTRAINT purchase_transaction_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(account_id)
);
CREATE TABLE public.purchase_transaction_items (
  item_id integer NOT NULL DEFAULT nextval('purchase_transaction_items_item_id_seq'::regclass),
  transaction_id integer NOT NULL,
  product_id integer NOT NULL,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  subtotal numeric DEFAULT ((quantity)::numeric * price),
  CONSTRAINT purchase_transaction_items_pkey PRIMARY KEY (item_id),
  CONSTRAINT purchase_transaction_items_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.purchase_transaction(transaction_id),
  CONSTRAINT purchase_transaction_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(productid)
);
CREATE TABLE public.sale (
  saleid integer NOT NULL DEFAULT nextval('sale_saleid_seq'::regclass),
  productid integer NOT NULL,
  warehouseid integer NOT NULL,
  customer_name character varying,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  total numeric DEFAULT ((quantity)::numeric * price),
  payment_type character varying NOT NULL CHECK (payment_type::text = ANY (ARRAY['cash'::character varying::text, 'credit'::character varying::text])),
  description text,
  date timestamp without time zone,
  CONSTRAINT sale_pkey PRIMARY KEY (saleid),
  CONSTRAINT sale_productid_fkey FOREIGN KEY (productid) REFERENCES public.product(productid),
  CONSTRAINT sale_warehouseid_fkey FOREIGN KEY (warehouseid) REFERENCES public.warehouse_list(warehouseid)
);
CREATE TABLE public.sale_return (
  return_id integer NOT NULL DEFAULT nextval('sale_return_return_id_seq'::regclass),
  store character varying NOT NULL,
  customer_name character varying,
  warehouse_id integer NOT NULL,
  total_amount numeric NOT NULL DEFAULT 0,
  return_type character varying NOT NULL CHECK (return_type::text = ANY (ARRAY['refund'::character varying, 'replacement'::character varying, 'store_credit'::character varying]::text[])),
  status character varying NOT NULL DEFAULT 'pending'::character varying CHECK (status::text = ANY (ARRAY['pending'::character varying, 'approved'::character varying, 'completed'::character varying, 'rejected'::character varying]::text[])),
  reason text,
  description text,
  account_id integer,
  return_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by character varying,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT sale_return_pkey PRIMARY KEY (return_id),
  CONSTRAINT sale_return_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouse_list(warehouseid),
  CONSTRAINT sale_return_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(account_id)
);
CREATE TABLE public.sale_return_items (
  item_id integer NOT NULL DEFAULT nextval('sale_return_items_item_id_seq'::regclass),
  return_id integer NOT NULL,
  product_id integer NOT NULL,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  subtotal numeric DEFAULT ((quantity)::numeric * price),
  CONSTRAINT sale_return_items_pkey PRIMARY KEY (item_id),
  CONSTRAINT sale_return_items_return_id_fkey FOREIGN KEY (return_id) REFERENCES public.sale_return(return_id),
  CONSTRAINT sale_return_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(productid)
);
CREATE TABLE public.sale_transaction (
  transaction_id integer NOT NULL DEFAULT nextval('sale_transaction_transaction_id_seq'::regclass),
  store character varying NOT NULL,
  warehouse_id integer NOT NULL,
  customer_name character varying,
  total_amount numeric NOT NULL DEFAULT 0,
  payment_type character varying NOT NULL CHECK (payment_type::text = ANY (ARRAY['cash'::character varying, 'credit'::character varying]::text[])),
  due_date timestamp without time zone,
  account_id integer,
  description text,
  transaction_date timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by character varying,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT sale_transaction_pkey PRIMARY KEY (transaction_id),
  CONSTRAINT sale_transaction_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES public.warehouse_list(warehouseid),
  CONSTRAINT sale_transaction_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(account_id)
);
CREATE TABLE public.sale_transaction_items (
  item_id integer NOT NULL DEFAULT nextval('sale_transaction_items_item_id_seq'::regclass),
  transaction_id integer NOT NULL,
  product_id integer NOT NULL,
  quantity integer NOT NULL,
  price numeric NOT NULL,
  subtotal numeric DEFAULT ((quantity)::numeric * price),
  CONSTRAINT sale_transaction_items_pkey PRIMARY KEY (item_id),
  CONSTRAINT sale_transaction_items_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.sale_transaction(transaction_id),
  CONSTRAINT sale_transaction_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.product(productid)
);
CREATE TABLE public.sales_payment_history (
  paymentid integer NOT NULL DEFAULT nextval('sales_payment_history_paymentid_seq'::regclass),
  saleid integer,
  amount_paid numeric NOT NULL,
  note text,
  paid_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT sales_payment_history_pkey PRIMARY KEY (paymentid),
  CONSTRAINT sales_payment_history_saleid_fkey FOREIGN KEY (saleid) REFERENCES public.sale(saleid)
);
CREATE TABLE public.stock_adjustment (
  adjustmentid integer NOT NULL DEFAULT nextval('stock_adjustment_adjustmentid_seq'::regclass),
  productid integer NOT NULL,
  warehouseid integer NOT NULL,
  type character varying NOT NULL CHECK (type::text = ANY (ARRAY['add'::character varying::text, 'reduce'::character varying::text])),
  quantity integer NOT NULL,
  description text,
  date timestamp without time zone,
  price numeric,
  store character varying,
  CONSTRAINT stock_adjustment_pkey PRIMARY KEY (adjustmentid),
  CONSTRAINT stock_adjustment_productid_fkey FOREIGN KEY (productid) REFERENCES public.product(productid),
  CONSTRAINT stock_adjustment_warehouseid_fkey FOREIGN KEY (warehouseid) REFERENCES public.warehouse_list(warehouseid)
);
CREATE TABLE public.supplier (
  supplierid integer NOT NULL DEFAULT nextval('supplier_supplierid_seq'::regclass),
  suppliername character varying NOT NULL,
  supplierno character varying,
  address text,
  description text,
  CONSTRAINT supplier_pkey PRIMARY KEY (supplierid)
);
CREATE TABLE public.users (
  user_id integer NOT NULL DEFAULT nextval('users_user_id_seq'::regclass),
  username character varying NOT NULL UNIQUE,
  password text NOT NULL,
  role character varying NOT NULL CHECK (role::text = ANY (ARRAY['admin'::character varying::text, 'pegawai'::character varying::text])),
  store character varying NOT NULL,
  CONSTRAINT users_pkey PRIMARY KEY (user_id)
);
CREATE TABLE public.warehouse_list (
  warehouseid integer NOT NULL DEFAULT nextval('warehouse_list_warehouseid_seq'::regclass),
  name character varying NOT NULL UNIQUE,
  CONSTRAINT warehouse_list_pkey PRIMARY KEY (warehouseid)
);