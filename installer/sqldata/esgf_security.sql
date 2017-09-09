--
-- PostgreSQL database dump
--

-- Dumped from database version 9.3.3
-- Dumped by pg_dump version 9.3.3
-- Started on 2016-06-20 11:43:29 MDT

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 8 (class 2615 OID 286169)
-- Name: esgf_security; Type: SCHEMA; Schema: -; Owner: dbsuper
--

CREATE SCHEMA esgf_security;


ALTER SCHEMA esgf_security OWNER TO dbsuper;

SET search_path = esgf_security, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 228 (class 1259 OID 286445)
-- Name: group; Type: TABLE; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

CREATE TABLE "group" (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL,
    visible boolean,
    automatic_approval boolean
);


ALTER TABLE esgf_security."group" OWNER TO dbsuper;

--
-- TOC entry 229 (class 1259 OID 286451)
-- Name: group_id_seq; Type: SEQUENCE; Schema: esgf_security; Owner: dbsuper
--

CREATE SEQUENCE group_id_seq
    START WITH 2
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE esgf_security.group_id_seq OWNER TO dbsuper;

--
-- TOC entry 2540 (class 0 OID 0)
-- Dependencies: 229
-- Name: group_id_seq; Type: SEQUENCE OWNED BY; Schema: esgf_security; Owner: dbsuper
--

ALTER SEQUENCE group_id_seq OWNED BY "group".id;


--
-- TOC entry 230 (class 1259 OID 286453)
-- Name: notification_types; Type: TABLE; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

CREATE TABLE notification_types (
    code integer NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL
);


ALTER TABLE esgf_security.notification_types OWNER TO dbsuper;

--
-- TOC entry 231 (class 1259 OID 286459)
-- Name: permission; Type: TABLE; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

CREATE TABLE permission (
    user_id integer NOT NULL,
    group_id integer NOT NULL,
    role_id integer NOT NULL,
    approved boolean DEFAULT false
);


ALTER TABLE esgf_security.permission OWNER TO dbsuper;

--
-- TOC entry 232 (class 1259 OID 286463)
-- Name: role; Type: TABLE; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

CREATE TABLE role (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text NOT NULL
);


ALTER TABLE esgf_security.role OWNER TO dbsuper;

--
-- TOC entry 233 (class 1259 OID 286469)
-- Name: role_id_seq; Type: SEQUENCE; Schema: esgf_security; Owner: dbsuper
--

CREATE SEQUENCE role_id_seq
    START WITH 2
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE esgf_security.role_id_seq OWNER TO dbsuper;

--
-- TOC entry 2541 (class 0 OID 0)
-- Dependencies: 233
-- Name: role_id_seq; Type: SEQUENCE OWNED BY; Schema: esgf_security; Owner: dbsuper
--

ALTER SEQUENCE role_id_seq OWNED BY role.id;


--
-- TOC entry 234 (class 1259 OID 286471)
-- Name: user; Type: TABLE; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

CREATE TABLE "user" (
    id integer NOT NULL,
    firstname character varying(100) NOT NULL,
    middlename character varying(100),
    lastname character varying(100) NOT NULL,
    email character varying(100) NOT NULL,
    username character varying(100) NOT NULL,
    password character varying(100),
    dn character varying(300),
    openid character varying(200) NOT NULL,
    organization character varying(200),
    organization_type character varying(200),
    city character varying(100),
    state character varying(100),
    country character varying(100),
    status_code integer,
    verification_token character varying(100),
    notification_code integer DEFAULT 0
);


ALTER TABLE esgf_security."user" OWNER TO dbsuper;

--
-- TOC entry 235 (class 1259 OID 286478)
-- Name: user_id_seq; Type: SEQUENCE; Schema: esgf_security; Owner: dbsuper
--

CREATE SEQUENCE user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE esgf_security.user_id_seq OWNER TO dbsuper;

--
-- TOC entry 2542 (class 0 OID 0)
-- Dependencies: 235
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: esgf_security; Owner: dbsuper
--

ALTER SEQUENCE user_id_seq OWNED BY "user".id;


--
-- TOC entry 2406 (class 2604 OID 286628)
-- Name: id; Type: DEFAULT; Schema: esgf_security; Owner: dbsuper
--

ALTER TABLE ONLY "group" ALTER COLUMN id SET DEFAULT nextval('group_id_seq'::regclass);


--
-- TOC entry 2408 (class 2604 OID 286629)
-- Name: id; Type: DEFAULT; Schema: esgf_security; Owner: dbsuper
--

ALTER TABLE ONLY role ALTER COLUMN id SET DEFAULT nextval('role_id_seq'::regclass);


--
-- TOC entry 2410 (class 2604 OID 286630)
-- Name: id; Type: DEFAULT; Schema: esgf_security; Owner: dbsuper
--

ALTER TABLE ONLY "user" ALTER COLUMN id SET DEFAULT nextval('user_id_seq'::regclass);


--
-- TOC entry 2412 (class 2606 OID 286691)
-- Name: group_name_key; Type: CONSTRAINT; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY "group"
    ADD CONSTRAINT group_name_key UNIQUE (name);


--
-- TOC entry 2414 (class 2606 OID 286693)
-- Name: group_pkey; Type: CONSTRAINT; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY "group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);


--
-- TOC entry 2416 (class 2606 OID 286695)
-- Name: permission_pkey; Type: CONSTRAINT; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY permission
    ADD CONSTRAINT permission_pkey PRIMARY KEY (user_id, group_id, role_id);


--
-- TOC entry 2418 (class 2606 OID 286697)
-- Name: role_name_key; Type: CONSTRAINT; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY role
    ADD CONSTRAINT role_name_key UNIQUE (name);


--
-- TOC entry 2420 (class 2606 OID 286699)
-- Name: role_pkey; Type: CONSTRAINT; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);


--
-- TOC entry 2423 (class 2606 OID 286701)
-- Name: user_openid_key; Type: CONSTRAINT; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_openid_key UNIQUE (openid);


--
-- TOC entry 2425 (class 2606 OID 286703)
-- Name: user_pkey; Type: CONSTRAINT; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- TOC entry 2421 (class 1259 OID 286756)
-- Name: ix_esgf_security_user_openid; Type: INDEX; Schema: esgf_security; Owner: dbsuper; Tablespace: 
--

CREATE INDEX ix_esgf_security_user_openid ON "user" USING btree (openid);


--
-- TOC entry 2426 (class 2606 OID 286799)
-- Name: permission_group_id_fkey; Type: FK CONSTRAINT; Schema: esgf_security; Owner: dbsuper
--

ALTER TABLE ONLY permission
    ADD CONSTRAINT permission_group_id_fkey FOREIGN KEY (group_id) REFERENCES "group"(id);


--
-- TOC entry 2427 (class 2606 OID 286804)
-- Name: permission_role_id_fkey; Type: FK CONSTRAINT; Schema: esgf_security; Owner: dbsuper
--

ALTER TABLE ONLY permission
    ADD CONSTRAINT permission_role_id_fkey FOREIGN KEY (role_id) REFERENCES role(id);


--
-- TOC entry 2428 (class 2606 OID 286809)
-- Name: permission_user_id_fkey; Type: FK CONSTRAINT; Schema: esgf_security; Owner: dbsuper
--

ALTER TABLE ONLY permission
    ADD CONSTRAINT permission_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


-- Completed on 2016-06-20 11:43:32 MDT

--
-- PostgreSQL database dump complete
--

