--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE ONLY public.transactions DROP CONSTRAINT transaction_user_id_fkey;
ALTER TABLE ONLY public.ai_works DROP CONSTRAINT ai_wroks_user_id_fkey;
ALTER TABLE ONLY public.ai_works DROP CONSTRAINT ai_wroks_debit_transaction_id_fkey;
ALTER TABLE ONLY public.users DROP CONSTRAINT users_pkey;
ALTER TABLE ONLY public.transactions DROP CONSTRAINT transaction_pkey;
ALTER TABLE ONLY public.settings DROP CONSTRAINT settings_pkey;
ALTER TABLE ONLY public.channels DROP CONSTRAINT channels_username_key;
ALTER TABLE ONLY public.channels DROP CONSTRAINT channels_pkey;
ALTER TABLE ONLY public.ai_works DROP CONSTRAINT ai_wroks_pkey;
ALTER TABLE public.users ALTER COLUMN telegram_id DROP DEFAULT;
ALTER TABLE public.transactions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.channels ALTER COLUMN id DROP DEFAULT;
ALTER TABLE public.ai_works ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE public.users_telegram_id_seq;
DROP TABLE public.users;
DROP SEQUENCE public.transaction_id_seq;
DROP TABLE public.transactions;
DROP TABLE public.settings;
DROP SEQUENCE public.channels_id_seq;
DROP TABLE public.channels;
DROP SEQUENCE public.ai_wroks_id_seq;
DROP TABLE public.ai_works;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_works; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ai_works (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    topic character varying(500) NOT NULL,
    work_type character varying(50) NOT NULL,
    page_range character varying(10) NOT NULL,
    cost numeric(10,2) NOT NULL,
    debit_transaction_id integer,
    is_completed boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ai_works OWNER TO postgres;

--
-- Name: ai_wroks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ai_wroks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ai_wroks_id_seq OWNER TO postgres;

--
-- Name: ai_wroks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ai_wroks_id_seq OWNED BY public.ai_works.id;


--
-- Name: channels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.channels (
    id integer NOT NULL,
    username text NOT NULL
);


ALTER TABLE public.channels OWNER TO postgres;

--
-- Name: channels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.channels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.channels_id_seq OWNER TO postgres;

--
-- Name: channels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.channels_id_seq OWNED BY public.channels.id;


--
-- Name: settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.settings (
    id character varying(50) NOT NULL,
    description text NOT NULL,
    comment character varying(255)
);


ALTER TABLE public.settings OWNER TO postgres;

--
-- Name: transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    amount numeric(10,2) NOT NULL,
    type character varying(50) NOT NULL,
    ai_work_id integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.transactions OWNER TO postgres;

--
-- Name: transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transaction_id_seq OWNER TO postgres;

--
-- Name: transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transaction_id_seq OWNED BY public.transactions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    telegram_id bigint NOT NULL,
    username character varying(255),
    balance numeric(10,2) DEFAULT 0.00 NOT NULL,
    registered_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    referrer_id bigint
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_telegram_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_telegram_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_telegram_id_seq OWNER TO postgres;

--
-- Name: users_telegram_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_telegram_id_seq OWNED BY public.users.telegram_id;


--
-- Name: ai_works id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_works ALTER COLUMN id SET DEFAULT nextval('public.ai_wroks_id_seq'::regclass);


--
-- Name: channels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels ALTER COLUMN id SET DEFAULT nextval('public.channels_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transaction_id_seq'::regclass);


--
-- Name: users telegram_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN telegram_id SET DEFAULT nextval('public.users_telegram_id_seq'::regclass);


--
-- Data for Name: ai_works; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ai_works (id, user_id, topic, work_type, page_range, cost, debit_transaction_id, is_completed, created_at) FROM stdin;
\.


--
-- Data for Name: channels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.channels (id, username) FROM stdin;
6	@talaba_express
\.


--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.settings (id, description, comment) FROM stdin;
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transactions (id, user_id, amount, type, ai_work_id, created_at) FROM stdin;
1	888632320	-5000.00	generation	\N	2025-10-11 11:35:47.238494+05
2	888632320	5000.00	admin_topup	\N	2025-10-13 12:25:55.229775+05
3	888632320	-5000.00	generation	\N	2025-10-13 12:26:54.154467+05
4	888632320	5000.00	admin_topup	\N	2025-10-13 12:51:51.811016+05
5	888632320	-4000.00	generation	\N	2025-10-13 12:52:42.654413+05
6	888632320	10000.00	admin_topup	\N	2025-10-13 14:04:53.911614+05
7	888632320	5000.00	admin_topup	\N	2025-10-13 14:15:36.257356+05
8	888632320	-4000.00	generation	\N	2025-10-13 14:38:04.051117+05
9	888632320	5000.00	admin_topup	\N	2025-10-13 14:49:57.886637+05
10	888632320	-4000.00	generation	\N	2025-10-13 14:55:28.215507+05
11	888632320	1000.00	admin_topup	\N	2025-10-13 17:02:49.562612+05
12	888632320	10000.00	admin_topup	\N	2025-10-13 17:05:29.136358+05
13	888632320	4000.00	admin_topup	\N	2025-10-13 21:32:31.132785+05
14	888632320	5785.00	admin_topup	\N	2025-10-14 02:38:06.063147+05
15	888632320	1.00	admin_topup	\N	2025-10-14 02:42:23.43238+05
16	888632320	212.00	admin_topup	\N	2025-10-14 02:43:01.508942+05
17	888632320	-4000.00	generation	\N	2025-10-14 02:49:49.945396+05
18	1265971438	-4000.00	generation	\N	2025-10-18 12:10:07.900501+05
19	5052391328	-4000.00	generation	\N	2025-10-18 12:28:43.515324+05
20	888632320	-4000.00	generation	\N	2025-10-18 13:13:24.71878+05
21	888632320	-4000.00	generation	\N	2025-10-18 15:20:27.398318+05
22	888632320	-10000.00	generation	\N	2025-10-19 21:07:40.519156+05
23	888632320	10000.00	admin_topup	\N	2025-10-19 23:27:16.193712+05
24	888632320	10000.00	admin_topup	\N	2025-10-20 00:30:47.857608+05
25	888632320	-12000.00	generation	\N	2025-10-20 11:17:47.373623+05
26	888632320	10000.00	admin_topup	\N	2025-10-20 11:44:32.263465+05
27	888632320	-10000.00	generation	\N	2025-10-20 12:01:30.55586+05
28	888632320	10000.00	rollback	\N	2025-10-20 12:04:13.055216+05
29	888632320	-10000.00	generation	\N	2025-10-20 12:06:03.954587+05
30	888632320	10000.00	rollback	\N	2025-10-20 12:06:49.310967+05
31	888632320	-10000.00	generation	\N	2025-10-20 12:09:49.837233+05
32	888632320	10000.00	rollback	\N	2025-10-20 12:10:35.253395+05
33	888632320	-10000.00	generation	\N	2025-10-20 12:13:17.065558+05
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (telegram_id, username, balance, registered_at, referrer_id) FROM stdin;
1265971438	Davronbek_Sharipov	1000.00	2025-10-18 12:09:48.49927+05	\N
5052391328	rashidov_bek	1000.00	2025-10-11 12:45:44.189805+05	\N
888632320	\N	25998.00	2025-10-11 11:15:38.268262+05	\N
\.


--
-- Name: ai_wroks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ai_wroks_id_seq', 1, false);


--
-- Name: channels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.channels_id_seq', 7, true);


--
-- Name: transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.transaction_id_seq', 33, true);


--
-- Name: users_telegram_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_telegram_id_seq', 1, false);


--
-- Name: ai_works ai_wroks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_works
    ADD CONSTRAINT ai_wroks_pkey PRIMARY KEY (id);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (id);


--
-- Name: channels channels_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_username_key UNIQUE (username);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (id);


--
-- Name: transactions transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transaction_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (telegram_id);


--
-- Name: ai_works ai_wroks_debit_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_works
    ADD CONSTRAINT ai_wroks_debit_transaction_id_fkey FOREIGN KEY (debit_transaction_id) REFERENCES public.transactions(id);


--
-- Name: ai_works ai_wroks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_works
    ADD CONSTRAINT ai_wroks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(telegram_id);


--
-- Name: transactions transaction_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transaction_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(telegram_id);


--
-- PostgreSQL database dump complete
--

