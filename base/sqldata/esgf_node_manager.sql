--
-- PostgreSQL database dump
--

-- Started on 2016-09-01 09:59:13 PDT

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

--
-- TOC entry 6 (class 2615 OID 16716)
-- Name: esgf_node_manager; Type: SCHEMA; Schema: -; Owner: dbsuper
--

CREATE SCHEMA esgf_node_manager;


ALTER SCHEMA esgf_node_manager OWNER TO dbsuper;

SET search_path = esgf_node_manager, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 175 (class 1259 OID 16717)
-- Dependencies: 2270 2271 6
-- Name: access_logging; Type: TABLE; Schema: esgf_node_manager; Owner: dbsuper; Tablespace: 
--

CREATE TABLE access_logging (
    id integer NOT NULL,
    user_id character varying NOT NULL,
    email character varying,
    url character varying NOT NULL,
    file_id character varying,
    remote_addr character varying NOT NULL,
    user_agent character varying,
    service_type character varying,
    batch_update_time double precision,
    date_fetched double precision NOT NULL,
    success boolean,
    duration double precision,
    user_id_hash character varying,
    user_idp character varying,
    data_size bigint DEFAULT (-1),
    xfer_size bigint DEFAULT (-1)
);


ALTER TABLE esgf_node_manager.access_logging OWNER TO dbsuper;

--
-- TOC entry 180 (class 1259 OID 16744)
-- Dependencies: 6 175
-- Name: access_logging_id_seq; Type: SEQUENCE; Schema: esgf_node_manager; Owner: dbsuper
--

CREATE SEQUENCE access_logging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE esgf_node_manager.access_logging_id_seq OWNER TO dbsuper;

--
-- TOC entry 2277 (class 0 OID 0)
-- Dependencies: 180
-- Name: access_logging_id_seq; Type: SEQUENCE OWNED BY; Schema: esgf_node_manager; Owner: dbsuper
--

ALTER SEQUENCE access_logging_id_seq OWNED BY access_logging.id;


--
-- TOC entry 176 (class 1259 OID 16723)
-- Dependencies: 6
-- Name: download; Type: TABLE; Schema: esgf_node_manager; Owner: dbsuper; Tablespace: 
--

CREATE TABLE download (
    userid character varying(64),
    url character varying(255)
);


ALTER TABLE esgf_node_manager.download OWNER TO dbsuper;

--
-- TOC entry 177 (class 1259 OID 16726)
-- Dependencies: 6
-- Name: metrics_run_log; Type: TABLE; Schema: esgf_node_manager; Owner: dbsuper; Tablespace: 
--

CREATE TABLE metrics_run_log (
    id character varying NOT NULL,
    last_run_time double precision
);


ALTER TABLE esgf_node_manager.metrics_run_log OWNER TO dbsuper;

--
-- TOC entry 178 (class 1259 OID 16732)
-- Dependencies: 6
-- Name: monitor_run_log; Type: TABLE; Schema: esgf_node_manager; Owner: dbsuper; Tablespace: 
--

CREATE TABLE monitor_run_log (
    id character varying NOT NULL,
    last_run_time double precision
);


ALTER TABLE esgf_node_manager.monitor_run_log OWNER TO dbsuper;

--
-- TOC entry 179 (class 1259 OID 16738)
-- Dependencies: 6
-- Name: notification_run_log; Type: TABLE; Schema: esgf_node_manager; Owner: dbsuper; Tablespace: 
--

CREATE TABLE notification_run_log (
    id character varying NOT NULL,
    notify_time double precision
);


ALTER TABLE esgf_node_manager.notification_run_log OWNER TO dbsuper;

--
-- TOC entry 2269 (class 2604 OID 16746)
-- Dependencies: 180 175
-- Name: id; Type: DEFAULT; Schema: esgf_node_manager; Owner: dbsuper
--

ALTER TABLE ONLY access_logging ALTER COLUMN id SET DEFAULT nextval('access_logging_id_seq'::regclass);


--
-- TOC entry 2273 (class 2606 OID 16748)
-- Dependencies: 175 175
-- Name: access_logging_pkey; Type: CONSTRAINT; Schema: esgf_node_manager; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY access_logging
    ADD CONSTRAINT access_logging_pkey PRIMARY KEY (id);


--
-- TOC entry 2274 (class 1259 OID 16749)
-- Dependencies: 175
-- Name: ix_esgf_node_manager_access_logging_url; Type: INDEX; Schema: esgf_node_manager; Owner: dbsuper; Tablespace: 
--

CREATE INDEX ix_esgf_node_manager_access_logging_url ON access_logging USING btree (url);


-- Completed on 2016-09-01 09:59:16 PDT

--
-- PostgreSQL database dump complete
--

