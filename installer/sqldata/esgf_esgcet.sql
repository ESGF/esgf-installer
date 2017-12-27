--
-- PostgreSQL database dump
--

-- Started on 2016-09-01 10:02:01 PDT

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 144 (class 1259 OID 16395)
-- Dependencies: 3
-- Name: catalog; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE catalog (
    dataset_name character varying(255) NOT NULL,
    version integer NOT NULL,
    location character varying(255) NOT NULL,
    rootpath character varying(255)
);


ALTER TABLE public.catalog OWNER TO esgcet;

--
-- TOC entry 165 (class 1259 OID 16494)
-- Dependencies: 3 144
-- Name: catalog_version_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE catalog_version_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.catalog_version_seq OWNER TO esgcet;

--
-- TOC entry 2376 (class 0 OID 0)
-- Dependencies: 165
-- Name: catalog_version_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE catalog_version_seq OWNED BY catalog.version;


--
-- TOC entry 145 (class 1259 OID 16398)
-- Dependencies: 3
-- Name: dataset; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE dataset (
    id integer NOT NULL,
    name character varying(255),
    project character varying(64),
    model character varying(64),
    experiment character varying(64),
    run_name character varying(64),
    calendar character varying(32),
    aggdim_name character varying(64),
    aggdim_units character varying(64),
    status_id character varying(64),
    offline boolean,
    master_gateway character varying(64)
);


ALTER TABLE public.dataset OWNER TO esgcet;

--
-- TOC entry 146 (class 1259 OID 16401)
-- Dependencies: 3
-- Name: dataset_attr; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE dataset_attr (
    dataset_id integer NOT NULL,
    name character varying(64) NOT NULL,
    value text NOT NULL,
    datatype character(1) NOT NULL,
    length integer NOT NULL,
    is_category boolean,
    is_thredds_category boolean
);


ALTER TABLE public.dataset_attr OWNER TO esgcet;

--
-- TOC entry 147 (class 1259 OID 16407)
-- Dependencies: 3
-- Name: dataset_file_version; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE dataset_file_version (
    dataset_version_id integer,
    file_version_id integer
);


ALTER TABLE public.dataset_file_version OWNER TO esgcet;

--
-- TOC entry 166 (class 1259 OID 16496)
-- Dependencies: 3 145
-- Name: dataset_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE dataset_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.dataset_id_seq OWNER TO esgcet;

--
-- TOC entry 2377 (class 0 OID 0)
-- Dependencies: 166
-- Name: dataset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE dataset_id_seq OWNED BY dataset.id;


--
-- TOC entry 148 (class 1259 OID 16410)
-- Dependencies: 3
-- Name: dataset_status; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE dataset_status (
    id integer NOT NULL,
    datetime timestamp without time zone,
    object_id integer,
    level integer,
    module integer,
    status text
);


ALTER TABLE public.dataset_status OWNER TO esgcet;

--
-- TOC entry 167 (class 1259 OID 16498)
-- Dependencies: 3 148
-- Name: dataset_status_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE dataset_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.dataset_status_id_seq OWNER TO esgcet;

--
-- TOC entry 2378 (class 0 OID 0)
-- Dependencies: 167
-- Name: dataset_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE dataset_status_id_seq OWNED BY dataset_status.id;


--
-- TOC entry 149 (class 1259 OID 16416)
-- Dependencies: 3
-- Name: dataset_version; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE dataset_version (
    id integer NOT NULL,
    dataset_id integer,
    version integer,
    name character varying(255),
    creation_time timestamp without time zone,
    comment text,
    tech_notes character varying(255),
    tech_notes_title character varying(255)
);


ALTER TABLE public.dataset_version OWNER TO esgcet;

--
-- TOC entry 168 (class 1259 OID 16500)
-- Dependencies: 3 149
-- Name: dataset_version_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE dataset_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.dataset_version_id_seq OWNER TO esgcet;

--
-- TOC entry 2379 (class 0 OID 0)
-- Dependencies: 168
-- Name: dataset_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE dataset_version_id_seq OWNED BY dataset_version.id;


--
-- TOC entry 174 (class 1259 OID 16708)
-- Dependencies: 3
-- Name: esgf_migrate_version; Type: TABLE; Schema: public; Owner: dbsuper; Tablespace: 
--

CREATE TABLE esgf_migrate_version (
    repository_id character varying(250) NOT NULL,
    repository_path text,
    version integer
);


ALTER TABLE public.esgf_migrate_version OWNER TO dbsuper;

--
-- TOC entry 150 (class 1259 OID 16425)
-- Dependencies: 3
-- Name: event; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE event (
    id integer NOT NULL,
    datetime timestamp without time zone NOT NULL,
    object_id integer,
    object_name character varying(255) NOT NULL,
    object_version integer,
    event integer
);


ALTER TABLE public.event OWNER TO esgcet;

--
-- TOC entry 169 (class 1259 OID 16502)
-- Dependencies: 3 150
-- Name: event_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.event_id_seq OWNER TO esgcet;

--
-- TOC entry 2380 (class 0 OID 0)
-- Dependencies: 169
-- Name: event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE event_id_seq OWNED BY event.id;


--
-- TOC entry 151 (class 1259 OID 16428)
-- Dependencies: 3
-- Name: experiment; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE experiment (
    name character varying(64) NOT NULL,
    project character varying(64) NOT NULL,
    description text
);


ALTER TABLE public.experiment OWNER TO esgcet;

--
-- TOC entry 152 (class 1259 OID 16434)
-- Dependencies: 3
-- Name: file; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE file (
    id integer NOT NULL,
    dataset_id integer NOT NULL,
    base character varying(255) NOT NULL,
    format character varying(16)
);


ALTER TABLE public.file OWNER TO esgcet;

--
-- TOC entry 153 (class 1259 OID 16437)
-- Dependencies: 3
-- Name: file_attr; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE file_attr (
    file_id integer NOT NULL,
    name character varying(64) NOT NULL,
    value text NOT NULL,
    datatype character(1) NOT NULL,
    length integer NOT NULL
);


ALTER TABLE public.file_attr OWNER TO esgcet;

--
-- TOC entry 170 (class 1259 OID 16504)
-- Dependencies: 3 152
-- Name: file_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE file_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.file_id_seq OWNER TO esgcet;

--
-- TOC entry 2381 (class 0 OID 0)
-- Dependencies: 170
-- Name: file_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE file_id_seq OWNED BY file.id;


--
-- TOC entry 154 (class 1259 OID 16443)
-- Dependencies: 3
-- Name: file_var_attr; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE file_var_attr (
    filevar_id integer NOT NULL,
    name character varying(64) NOT NULL,
    value text NOT NULL,
    datatype character(1) NOT NULL,
    length integer NOT NULL
);


ALTER TABLE public.file_var_attr OWNER TO esgcet;

--
-- TOC entry 155 (class 1259 OID 16449)
-- Dependencies: 3
-- Name: file_variable; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE file_variable (
    id integer NOT NULL,
    file_id integer NOT NULL,
    variable_id integer,
    short_name character varying(255) NOT NULL,
    long_name character varying(255),
    aggdim_first double precision,
    aggdim_last double precision,
    aggdim_units character varying(64),
    coord_range character varying(32),
    coord_type character varying(8),
    coord_values text
);


ALTER TABLE public.file_variable OWNER TO esgcet;

--
-- TOC entry 171 (class 1259 OID 16506)
-- Dependencies: 3 155
-- Name: file_variable_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE file_variable_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.file_variable_id_seq OWNER TO esgcet;

--
-- TOC entry 2382 (class 0 OID 0)
-- Dependencies: 171
-- Name: file_variable_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE file_variable_id_seq OWNED BY file_variable.id;


--
-- TOC entry 156 (class 1259 OID 16455)
-- Dependencies: 3
-- Name: file_version; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE file_version (
    id integer NOT NULL,
    file_id integer,
    version integer,
    location text NOT NULL,
    size bigint,
    checksum character varying(64),
    checksum_type character varying(32),
    publication_time timestamp without time zone,
    tracking_id character varying(64),
    mod_time double precision,
    url text,
    tech_notes character varying(255),
    tech_notes_title character varying(255)
);


ALTER TABLE public.file_version OWNER TO esgcet;

--
-- TOC entry 172 (class 1259 OID 16508)
-- Dependencies: 156 3
-- Name: file_version_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE file_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.file_version_id_seq OWNER TO esgcet;

--
-- TOC entry 2383 (class 0 OID 0)
-- Dependencies: 172
-- Name: file_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE file_version_id_seq OWNED BY file_version.id;


--
-- TOC entry 157 (class 1259 OID 16458)
-- Dependencies: 3
-- Name: filevar_dimension; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE filevar_dimension (
    filevar_id integer NOT NULL,
    name character varying(64) NOT NULL,
    length integer NOT NULL,
    seq integer NOT NULL
);


ALTER TABLE public.filevar_dimension OWNER TO esgcet;

--
-- TOC entry 158 (class 1259 OID 16461)
-- Dependencies: 3
-- Name: las_catalog; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE las_catalog (
    dataset_name character varying(255) NOT NULL,
    location character varying(255) NOT NULL
);


ALTER TABLE public.las_catalog OWNER TO esgcet;

--
-- TOC entry 143 (class 1259 OID 16387)
-- Dependencies: 3
-- Name: migrate_version; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE migrate_version (
    repository_id character varying(250) NOT NULL,
    repository_path text,
    version integer
);


ALTER TABLE public.migrate_version OWNER TO esgcet;

--
-- TOC entry 159 (class 1259 OID 16464)
-- Dependencies: 3
-- Name: model; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE model (
    name character varying(64) NOT NULL,
    project character varying(64) NOT NULL,
    url character varying(128),
    description text
);


ALTER TABLE public.model OWNER TO esgcet;

--
-- TOC entry 160 (class 1259 OID 16470)
-- Dependencies: 3
-- Name: project; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE project (
    name character varying(64) NOT NULL,
    description character varying(64)
);


ALTER TABLE public.project OWNER TO esgcet;

--
-- TOC entry 161 (class 1259 OID 16473)
-- Dependencies: 3
-- Name: standard_name; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE standard_name (
    name character varying(255) NOT NULL,
    units character varying(64),
    amip character varying(64),
    grib character varying(64),
    description text
);


ALTER TABLE public.standard_name OWNER TO esgcet;

--
-- TOC entry 162 (class 1259 OID 16479)
-- Dependencies: 3
-- Name: var_attr; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE var_attr (
    variable_id integer NOT NULL,
    name character varying(64) NOT NULL,
    value text NOT NULL,
    datatype character(1) NOT NULL,
    length integer NOT NULL
);


ALTER TABLE public.var_attr OWNER TO esgcet;

--
-- TOC entry 163 (class 1259 OID 16485)
-- Dependencies: 3
-- Name: var_dimension; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE var_dimension (
    variable_id integer NOT NULL,
    name character varying(64) NOT NULL,
    length integer NOT NULL,
    seq integer NOT NULL
);


ALTER TABLE public.var_dimension OWNER TO esgcet;

--
-- TOC entry 164 (class 1259 OID 16488)
-- Dependencies: 3
-- Name: variable; Type: TABLE; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE TABLE variable (
    id integer NOT NULL,
    dataset_id integer,
    short_name character varying(255),
    long_name character varying(255),
    standard_name character varying(255),
    vertical_granularity character varying(64),
    grid integer,
    aggdim_first double precision,
    aggdim_last double precision,
    units character varying(64),
    has_errors boolean,
    eastwest_range character varying(64),
    northsouth_range character varying(64),
    updown_range character varying(64),
    updown_values text
);


ALTER TABLE public.variable OWNER TO esgcet;

--
-- TOC entry 173 (class 1259 OID 16510)
-- Dependencies: 3 164
-- Name: variable_id_seq; Type: SEQUENCE; Schema: public; Owner: esgcet
--

CREATE SEQUENCE variable_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.variable_id_seq OWNER TO esgcet;

--
-- TOC entry 2384 (class 0 OID 0)
-- Dependencies: 173
-- Name: variable_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: esgcet
--

ALTER SEQUENCE variable_id_seq OWNED BY variable.id;


--
-- TOC entry 2287 (class 2604 OID 16512)
-- Dependencies: 165 144
-- Name: version; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY catalog ALTER COLUMN version SET DEFAULT nextval('catalog_version_seq'::regclass);


--
-- TOC entry 2288 (class 2604 OID 16513)
-- Dependencies: 166 145
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset ALTER COLUMN id SET DEFAULT nextval('dataset_id_seq'::regclass);


--
-- TOC entry 2289 (class 2604 OID 16514)
-- Dependencies: 167 148
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset_status ALTER COLUMN id SET DEFAULT nextval('dataset_status_id_seq'::regclass);


--
-- TOC entry 2290 (class 2604 OID 16515)
-- Dependencies: 168 149
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset_version ALTER COLUMN id SET DEFAULT nextval('dataset_version_id_seq'::regclass);


--
-- TOC entry 2291 (class 2604 OID 16516)
-- Dependencies: 169 150
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY event ALTER COLUMN id SET DEFAULT nextval('event_id_seq'::regclass);


--
-- TOC entry 2292 (class 2604 OID 16517)
-- Dependencies: 170 152
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file ALTER COLUMN id SET DEFAULT nextval('file_id_seq'::regclass);


--
-- TOC entry 2293 (class 2604 OID 16518)
-- Dependencies: 171 155
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file_variable ALTER COLUMN id SET DEFAULT nextval('file_variable_id_seq'::regclass);


--
-- TOC entry 2294 (class 2604 OID 16519)
-- Dependencies: 172 156
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file_version ALTER COLUMN id SET DEFAULT nextval('file_version_id_seq'::regclass);


--
-- TOC entry 2295 (class 2604 OID 16520)
-- Dependencies: 173 164
-- Name: id; Type: DEFAULT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY variable ALTER COLUMN id SET DEFAULT nextval('variable_id_seq'::regclass);


--
-- TOC entry 2299 (class 2606 OID 16522)
-- Dependencies: 144 144 144
-- Name: catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY catalog
    ADD CONSTRAINT catalog_pkey PRIMARY KEY (dataset_name, version);


--
-- TOC entry 2305 (class 2606 OID 16524)
-- Dependencies: 146 146 146
-- Name: dataset_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY dataset_attr
    ADD CONSTRAINT dataset_attr_pkey PRIMARY KEY (dataset_id, name);


--
-- TOC entry 2301 (class 2606 OID 16526)
-- Dependencies: 145 145
-- Name: dataset_name_key; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_name_key UNIQUE (name);


--
-- TOC entry 2303 (class 2606 OID 16528)
-- Dependencies: 145 145
-- Name: dataset_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);


--
-- TOC entry 2308 (class 2606 OID 16530)
-- Dependencies: 148 148
-- Name: dataset_status_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY dataset_status
    ADD CONSTRAINT dataset_status_pkey PRIMARY KEY (id);


--
-- TOC entry 2310 (class 2606 OID 16532)
-- Dependencies: 149 149
-- Name: dataset_version_name_key; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY dataset_version
    ADD CONSTRAINT dataset_version_name_key UNIQUE (name);


--
-- TOC entry 2312 (class 2606 OID 16534)
-- Dependencies: 149 149
-- Name: dataset_version_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY dataset_version
    ADD CONSTRAINT dataset_version_pkey PRIMARY KEY (id);


--
-- TOC entry 2350 (class 2606 OID 16715)
-- Dependencies: 174 174
-- Name: esgf_migrate_version_pkey; Type: CONSTRAINT; Schema: public; Owner: dbsuper; Tablespace: 
--

ALTER TABLE ONLY esgf_migrate_version
    ADD CONSTRAINT esgf_migrate_version_pkey PRIMARY KEY (repository_id);


--
-- TOC entry 2315 (class 2606 OID 16536)
-- Dependencies: 150 150
-- Name: event_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY event
    ADD CONSTRAINT event_pkey PRIMARY KEY (id);


--
-- TOC entry 2318 (class 2606 OID 16538)
-- Dependencies: 151 151 151
-- Name: experiment_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY experiment
    ADD CONSTRAINT experiment_pkey PRIMARY KEY (name, project);


--
-- TOC entry 2322 (class 2606 OID 16540)
-- Dependencies: 153 153 153
-- Name: file_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY file_attr
    ADD CONSTRAINT file_attr_pkey PRIMARY KEY (file_id, name);


--
-- TOC entry 2320 (class 2606 OID 16542)
-- Dependencies: 152 152
-- Name: file_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_pkey PRIMARY KEY (id);


--
-- TOC entry 2324 (class 2606 OID 16544)
-- Dependencies: 154 154 154
-- Name: file_var_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY file_var_attr
    ADD CONSTRAINT file_var_attr_pkey PRIMARY KEY (filevar_id, name);


--
-- TOC entry 2327 (class 2606 OID 16546)
-- Dependencies: 155 155
-- Name: file_variable_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY file_variable
    ADD CONSTRAINT file_variable_pkey PRIMARY KEY (id);


--
-- TOC entry 2332 (class 2606 OID 16548)
-- Dependencies: 156 156
-- Name: file_version_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY file_version
    ADD CONSTRAINT file_version_pkey PRIMARY KEY (id);


--
-- TOC entry 2334 (class 2606 OID 16550)
-- Dependencies: 157 157 157
-- Name: filevar_dimension_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY filevar_dimension
    ADD CONSTRAINT filevar_dimension_pkey PRIMARY KEY (filevar_id, name);


--
-- TOC entry 2336 (class 2606 OID 16552)
-- Dependencies: 158 158
-- Name: las_catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY las_catalog
    ADD CONSTRAINT las_catalog_pkey PRIMARY KEY (dataset_name);


--
-- TOC entry 2297 (class 2606 OID 16394)
-- Dependencies: 143 143
-- Name: migrate_version_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY migrate_version
    ADD CONSTRAINT migrate_version_pkey PRIMARY KEY (repository_id);


--
-- TOC entry 2338 (class 2606 OID 16554)
-- Dependencies: 159 159 159
-- Name: model_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY model
    ADD CONSTRAINT model_pkey PRIMARY KEY (name, project);


--
-- TOC entry 2340 (class 2606 OID 16556)
-- Dependencies: 160 160
-- Name: project_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY project
    ADD CONSTRAINT project_pkey PRIMARY KEY (name);


--
-- TOC entry 2342 (class 2606 OID 16674)
-- Dependencies: 161 161
-- Name: standard_name_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY standard_name
    ADD CONSTRAINT standard_name_pkey PRIMARY KEY (name);


--
-- TOC entry 2344 (class 2606 OID 16560)
-- Dependencies: 162 162 162
-- Name: var_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY var_attr
    ADD CONSTRAINT var_attr_pkey PRIMARY KEY (variable_id, name);


--
-- TOC entry 2346 (class 2606 OID 16562)
-- Dependencies: 163 163 163
-- Name: var_dimension_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY var_dimension
    ADD CONSTRAINT var_dimension_pkey PRIMARY KEY (variable_id, name);


--
-- TOC entry 2348 (class 2606 OID 16564)
-- Dependencies: 164 164
-- Name: variable_pkey; Type: CONSTRAINT; Schema: public; Owner: esgcet; Tablespace: 
--

ALTER TABLE ONLY variable
    ADD CONSTRAINT variable_pkey PRIMARY KEY (id);


--
-- TOC entry 2306 (class 1259 OID 16701)
-- Dependencies: 147
-- Name: dataset_file_version_id_index; Type: INDEX; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE INDEX dataset_file_version_id_index ON dataset_file_version USING btree (file_version_id);


--
-- TOC entry 2313 (class 1259 OID 16565)
-- Dependencies: 149
-- Name: datasetversion_index; Type: INDEX; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE UNIQUE INDEX datasetversion_index ON dataset_version USING btree (name);


--
-- TOC entry 2325 (class 1259 OID 16700)
-- Dependencies: 155
-- Name: file_variable_file_id_index; Type: INDEX; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE INDEX file_variable_file_id_index ON file_variable USING btree (file_id);


--
-- TOC entry 2328 (class 1259 OID 16699)
-- Dependencies: 155
-- Name: file_variable_variable_id_index; Type: INDEX; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE INDEX file_variable_variable_id_index ON file_variable USING btree (variable_id);


--
-- TOC entry 2330 (class 1259 OID 16702)
-- Dependencies: 156
-- Name: file_version_file_id_index; Type: INDEX; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE INDEX file_version_file_id_index ON file_version USING btree (file_id);


--
-- TOC entry 2329 (class 1259 OID 16566)
-- Dependencies: 155 155
-- Name: filevar_index; Type: INDEX; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE UNIQUE INDEX filevar_index ON file_variable USING btree (file_id, variable_id);


--
-- TOC entry 2316 (class 1259 OID 16567)
-- Dependencies: 150
-- Name: ix_event_datetime; Type: INDEX; Schema: public; Owner: esgcet; Tablespace: 
--

CREATE INDEX ix_event_datetime ON event USING btree (datetime);


--
-- TOC entry 2353 (class 2606 OID 16568)
-- Dependencies: 146 145 2302
-- Name: dataset_attr_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset_attr
    ADD CONSTRAINT dataset_attr_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES dataset(id);


--
-- TOC entry 2351 (class 2606 OID 16573)
-- Dependencies: 2317 151 145 145 151
-- Name: dataset_experiment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_experiment_fkey FOREIGN KEY (experiment, project) REFERENCES experiment(name, project);


--
-- TOC entry 2354 (class 2606 OID 16578)
-- Dependencies: 149 147 2311
-- Name: dataset_file_version_dataset_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset_file_version
    ADD CONSTRAINT dataset_file_version_dataset_version_id_fkey FOREIGN KEY (dataset_version_id) REFERENCES dataset_version(id);


--
-- TOC entry 2355 (class 2606 OID 16583)
-- Dependencies: 156 147 2331
-- Name: dataset_file_version_file_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset_file_version
    ADD CONSTRAINT dataset_file_version_file_version_id_fkey FOREIGN KEY (file_version_id) REFERENCES file_version(id);


--
-- TOC entry 2352 (class 2606 OID 16588)
-- Dependencies: 159 145 145 159 2337
-- Name: dataset_model_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset
    ADD CONSTRAINT dataset_model_fkey FOREIGN KEY (model, project) REFERENCES model(name, project);


--
-- TOC entry 2356 (class 2606 OID 16593)
-- Dependencies: 145 148 2302
-- Name: dataset_status_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset_status
    ADD CONSTRAINT dataset_status_object_id_fkey FOREIGN KEY (object_id) REFERENCES dataset(id);


--
-- TOC entry 2357 (class 2606 OID 16598)
-- Dependencies: 149 2302 145
-- Name: dataset_version_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY dataset_version
    ADD CONSTRAINT dataset_version_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES dataset(id);


--
-- TOC entry 2358 (class 2606 OID 16603)
-- Dependencies: 2302 150 145
-- Name: event_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY event
    ADD CONSTRAINT event_object_id_fkey FOREIGN KEY (object_id) REFERENCES dataset(id);


--
-- TOC entry 2359 (class 2606 OID 16608)
-- Dependencies: 160 2339 151
-- Name: experiment_project_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY experiment
    ADD CONSTRAINT experiment_project_fkey FOREIGN KEY (project) REFERENCES project(name);


--
-- TOC entry 2361 (class 2606 OID 16613)
-- Dependencies: 2319 153 152
-- Name: file_attr_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file_attr
    ADD CONSTRAINT file_attr_file_id_fkey FOREIGN KEY (file_id) REFERENCES file(id);


--
-- TOC entry 2360 (class 2606 OID 16618)
-- Dependencies: 2302 152 145
-- Name: file_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file
    ADD CONSTRAINT file_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES dataset(id);


--
-- TOC entry 2362 (class 2606 OID 16623)
-- Dependencies: 155 154 2326
-- Name: file_var_attr_filevar_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file_var_attr
    ADD CONSTRAINT file_var_attr_filevar_id_fkey FOREIGN KEY (filevar_id) REFERENCES file_variable(id);


--
-- TOC entry 2363 (class 2606 OID 16628)
-- Dependencies: 155 152 2319
-- Name: file_variable_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file_variable
    ADD CONSTRAINT file_variable_file_id_fkey FOREIGN KEY (file_id) REFERENCES file(id);


--
-- TOC entry 2364 (class 2606 OID 16633)
-- Dependencies: 155 164 2347
-- Name: file_variable_variable_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file_variable
    ADD CONSTRAINT file_variable_variable_id_fkey FOREIGN KEY (variable_id) REFERENCES variable(id);


--
-- TOC entry 2365 (class 2606 OID 16638)
-- Dependencies: 156 2319 152
-- Name: file_version_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY file_version
    ADD CONSTRAINT file_version_file_id_fkey FOREIGN KEY (file_id) REFERENCES file(id);


--
-- TOC entry 2366 (class 2606 OID 16643)
-- Dependencies: 157 2326 155
-- Name: filevar_dimension_filevar_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY filevar_dimension
    ADD CONSTRAINT filevar_dimension_filevar_id_fkey FOREIGN KEY (filevar_id) REFERENCES file_variable(id);


--
-- TOC entry 2367 (class 2606 OID 16648)
-- Dependencies: 2339 159 160
-- Name: model_project_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY model
    ADD CONSTRAINT model_project_fkey FOREIGN KEY (project) REFERENCES project(name);


--
-- TOC entry 2368 (class 2606 OID 16653)
-- Dependencies: 162 2347 164
-- Name: var_attr_variable_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY var_attr
    ADD CONSTRAINT var_attr_variable_id_fkey FOREIGN KEY (variable_id) REFERENCES variable(id);


--
-- TOC entry 2369 (class 2606 OID 16658)
-- Dependencies: 2347 163 164
-- Name: var_dimension_variable_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY var_dimension
    ADD CONSTRAINT var_dimension_variable_id_fkey FOREIGN KEY (variable_id) REFERENCES variable(id);


--
-- TOC entry 2370 (class 2606 OID 16663)
-- Dependencies: 2302 164 145
-- Name: variable_dataset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY variable
    ADD CONSTRAINT variable_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES dataset(id);


--
-- TOC entry 2371 (class 2606 OID 16687)
-- Dependencies: 164 161 2341
-- Name: variable_standard_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: esgcet
--

ALTER TABLE ONLY variable
    ADD CONSTRAINT variable_standard_name_fkey FOREIGN KEY (standard_name) REFERENCES standard_name(name);


--
-- TOC entry 2375 (class 0 OID 0)
-- Dependencies: 3
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2016-09-01 10:02:05 PDT

--
-- PostgreSQL database dump complete
--

