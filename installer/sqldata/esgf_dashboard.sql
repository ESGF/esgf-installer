DROP SCHEMA IF EXISTS esgf_dashboard CASCADE;
CREATE SCHEMA esgf_dashboard;

-- ----------------------------
-- Table structure for `continent`
-- ----------------------------
DROP TABLE IF EXISTS esgf_dashboard.continent;
CREATE TABLE esgf_dashboard.continent (
  continent_code character(2) PRIMARY KEY,
  continent_name character varying(255),
  latitude numeric(14,11),
  longitude numeric(14,11)
);

-- ----------------------------
-- Records of continents
-- ----------------------------
INSERT INTO esgf_dashboard.continent VALUES ('AF', 'Africa', 7.18805555556, 21.0936111111);
INSERT INTO esgf_dashboard.continent VALUES ('AN', 'Antarctica', -83.3594444444, 16.5233333333);
INSERT INTO esgf_dashboard.continent VALUES ('AS', 'Asia', 29.8405555556, 89.2966666667);
INSERT INTO esgf_dashboard.continent VALUES ('EU', 'Europe', 48.6908333333, 9.14055555556);
INSERT INTO esgf_dashboard.continent VALUES ('NA', 'North America', 46.0730555556, -100.546666667);
INSERT INTO esgf_dashboard.continent VALUES ('OC', 'Oceania', -18.3127777778, 138.515555556);
INSERT INTO esgf_dashboard.continent VALUES ('SA', 'South America', -14.6047222222, -57.6561111111);

-- ----------------------------
-- Table structure for `country`
-- ----------------------------
DROP TABLE IF EXISTS esgf_dashboard.country;
CREATE TABLE esgf_dashboard.country (
  country_id serial PRIMARY KEY,
  country_code character(2) NOT NULL,
  country_name character varying(64) NOT NULL,
  continent_code character(2) NOT NULL REFERENCES esgf_dashboard.continent
);

-- ----------------------------
-- Records of countries
-- ----------------------------
INSERT INTO esgf_dashboard.country VALUES ('1', 'AD', 'Andorra', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('2', 'AE', 'United Arab Emirates', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('3', 'AF', 'Afghanistan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('4', 'AG', 'Antigua and Barbuda', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('5', 'AI', 'Anguilla', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('6', 'AL', 'Albania', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('7', 'AM', 'Armenia', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('8', 'AN', 'Netherlands Antilles', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('9', 'AO', 'Angola', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('10', 'AQ', 'Antarctica', 'AN');
INSERT INTO esgf_dashboard.country VALUES ('11', 'AR', 'Argentina', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('12', 'AS', 'American Samoa', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('13', 'AT', 'Austria', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('14', 'AU', 'Australia', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('15', 'AW', 'Aruba', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('16', 'AX', 'Åland', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('17', 'AZ', 'Azerbaijan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('18', 'BA', 'Bosnia and Herzegovina', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('19', 'BB', 'Barbados', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('20', 'BD', 'Bangladesh', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('21', 'BE', 'Belgium', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('22', 'BF', 'Burkina Faso', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('23', 'BG', 'Bulgaria', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('24', 'BH', 'Bahrain', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('25', 'BI', 'Burundi', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('26', 'BJ', 'Benin', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('27', 'BL', 'Saint Barthélemy', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('28', 'BM', 'Bermuda', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('29', 'BN', 'Brunei Darussalam', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('30', 'BO', 'Bolivia', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('31', 'BR', 'Brazil', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('32', 'BS', 'Bahamas', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('33', 'BT', 'Bhutan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('34', 'BV', 'Bouvet Island', 'AN');
INSERT INTO esgf_dashboard.country VALUES ('35', 'BW', 'Botswana', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('36', 'BY', 'Belarus', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('37', 'BZ', 'Belize', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('38', 'CA', 'Canada', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('39', 'CC', 'Cocos (Keeling) Islands', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('40', 'CD', 'Congo (Kinshasa)', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('41', 'CF', 'Central African Republic', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('42', 'CG', 'Congo (Brazzaville)', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('43', 'CH', 'Switzerland', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('44', 'CI', 'Côte d''Ivoire', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('45', 'CK', 'Cook Islands', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('46', 'CL', 'Chile', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('47', 'CM', 'Cameroon', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('48', 'CN', 'China', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('49', 'CO', 'Colombia', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('50', 'CR', 'Costa Rica', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('51', 'CU', 'Cuba', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('52', 'CV', 'Cape Verde', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('53', 'CX', 'Christmas Island', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('54', 'CY', 'Cyprus', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('55', 'CZ', 'Czech Republic', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('56', 'DE', 'Germany', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('57', 'DJ', 'Djibouti', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('58', 'DK', 'Denmark', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('59', 'DM', 'Dominica', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('60', 'DO', 'Dominican Republic', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('61', 'DZ', 'Algeria', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('62', 'EC', 'Ecuador', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('63', 'EE', 'Estonia', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('64', 'EG', 'Egypt', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('65', 'EH', 'Western Sahara', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('66', 'ER', 'Eritrea', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('67', 'ES', 'Spain', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('68', 'ET', 'Ethiopia', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('69', 'FI', 'Finland', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('70', 'FJ', 'Fiji', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('71', 'FK', 'Falkland Islands', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('72', 'FM', 'Micronesia', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('73', 'FO', 'Faroe Islands', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('74', 'FR', 'France', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('75', 'GA', 'Gabon', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('76', 'GB', 'United Kingdom', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('77', 'GD', 'Grenada', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('78', 'GE', 'Georgia', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('79', 'GF', 'French Guiana', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('80', 'GG', 'Guernsey', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('81', 'GH', 'Ghana', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('82', 'GI', 'Gibraltar', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('83', 'GL', 'Greenland', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('84', 'GM', 'Gambia', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('85', 'GN', 'Guinea', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('86', 'GP', 'Guadeloupe', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('87', 'GQ', 'Equatorial Guinea', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('88', 'GR', 'Greece', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('89', 'GS', 'South Georgia and South Sandwich Islands', 'AN');
INSERT INTO esgf_dashboard.country VALUES ('90', 'GT', 'Guatemala', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('91', 'GU', 'Guam', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('92', 'GW', 'Guinea-Bissau', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('93', 'GY', 'Guyana', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('94', 'HK', 'Hong Kong', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('95', 'HM', 'Heard and McDonald Islands', 'AN');
INSERT INTO esgf_dashboard.country VALUES ('96', 'HN', 'Honduras', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('97', 'HR', 'Croatia', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('98', 'HT', 'Haiti', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('99', 'HU', 'Hungary', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('100', 'ID', 'Indonesia', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('101', 'IE', 'Ireland', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('102', 'IL', 'Israel', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('103', 'IM', 'Isle of Man', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('104', 'IN', 'India', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('105', 'IO', 'British Indian Ocean Territory', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('106', 'IQ', 'Iraq', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('107', 'IR', 'Iran', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('108', 'IS', 'Iceland', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('109', 'IT', 'Italy', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('110', 'JE', 'Jersey', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('111', 'JM', 'Jamaica', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('112', 'JO', 'Jordan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('113', 'JP', 'Japan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('114', 'KE', 'Kenya', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('115', 'KG', 'Kyrgyzstan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('116', 'KH', 'Cambodia', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('117', 'KI', 'Kiribati', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('118', 'KM', 'Comoros', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('119', 'KN', 'Saint Kitts and Nevis', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('120', 'KP', 'Korea, North', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('121', 'KR', 'Korea, South', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('122', 'KW', 'Kuwait', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('123', 'KY', 'Cayman Islands', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('124', 'KZ', 'Kazakhstan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('125', 'LA', 'Laos', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('126', 'LB', 'Lebanon', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('127', 'LC', 'Saint Lucia', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('128', 'LI', 'Liechtenstein', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('129', 'LK', 'Sri Lanka', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('130', 'LR', 'Liberia', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('131', 'LS', 'Lesotho', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('132', 'LT', 'Lithuania', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('133', 'LU', 'Luxembourg', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('134', 'LV', 'Latvia', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('135', 'LY', 'Libya', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('136', 'MA', 'Morocco', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('137', 'MC', 'Monaco', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('138', 'MD', 'Moldova', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('139', 'ME', 'Montenegro', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('140', 'MF', 'Saint Martin (French part)', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('141', 'MG', 'Madagascar', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('142', 'MH', 'Marshall Islands', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('143', 'MK', 'Macedonia', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('144', 'ML', 'Mali', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('145', 'MM', 'Myanmar', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('146', 'MN', 'Mongolia', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('147', 'MO', 'Macau', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('148', 'MP', 'Northern Mariana Islands', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('149', 'MQ', 'Martinique', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('150', 'MR', 'Mauritania', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('151', 'MS', 'Montserrat', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('152', 'MT', 'Malta', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('153', 'MU', 'Mauritius', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('154', 'MV', 'Maldives', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('155', 'MW', 'Malawi', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('156', 'MX', 'Mexico', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('157', 'MY', 'Malaysia', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('158', 'MZ', 'Mozambique', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('159', 'NA', 'Namibia', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('160', 'NC', 'New Caledonia', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('161', 'NE', 'Niger', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('162', 'NF', 'Norfolk Island', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('163', 'NG', 'Nigeria', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('164', 'NI', 'Nicaragua', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('165', 'NL', 'Netherlands', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('166', 'NO', 'Norway', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('167', 'NP', 'Nepal', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('168', 'NR', 'Nauru', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('169', 'NU', 'Niue', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('170', 'NZ', 'New Zealand', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('171', 'OM', 'Oman', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('172', 'PA', 'Panama', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('173', 'PE', 'Peru', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('174', 'PF', 'French Polynesia', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('175', 'PG', 'Papua New Guinea', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('176', 'PH', 'Philippines', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('177', 'PK', 'Pakistan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('178', 'PL', 'Poland', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('179', 'PM', 'Saint Pierre and Miquelon', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('180', 'PN', 'Pitcairn', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('181', 'PR', 'Puerto Rico', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('182', 'PS', 'Palestine', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('183', 'PT', 'Portugal', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('184', 'PW', 'Palau', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('185', 'PY', 'Paraguay', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('186', 'QA', 'Qatar', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('187', 'RE', 'Reunion', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('188', 'RO', 'Romania', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('189', 'RS', 'Serbia', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('190', 'RU', 'Russian Federation', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('191', 'RW', 'Rwanda', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('192', 'SA', 'Saudi Arabia', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('193', 'SB', 'Solomon Islands', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('194', 'SC', 'Seychelles', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('195', 'SD', 'Sudan', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('196', 'SE', 'Sweden', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('197', 'SG', 'Singapore', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('198', 'SH', 'Saint Helena', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('199', 'SI', 'Slovenia', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('200', 'SJ', 'Svalbard and Jan Mayen Islands', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('201', 'SK', 'Slovakia', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('202', 'SL', 'Sierra Leone', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('203', 'SM', 'San Marino', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('204', 'SN', 'Senegal', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('205', 'SO', 'Somalia', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('206', 'SR', 'Suriname', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('207', 'ST', 'Sao Tome and Principe', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('208', 'SV', 'El Salvador', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('209', 'SY', 'Syria', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('210', 'SZ', 'Swaziland', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('211', 'TC', 'Turks and Caicos Islands', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('212', 'TD', 'Chad', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('213', 'TF', 'French Southern Lands', 'AN');
INSERT INTO esgf_dashboard.country VALUES ('214', 'TG', 'Togo', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('215', 'TH', 'Thailand', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('216', 'TJ', 'Tajikistan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('217', 'TK', 'Tokelau', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('218', 'TL', 'Timor-Leste', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('219', 'TM', 'Turkmenistan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('220', 'TN', 'Tunisia', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('221', 'TO', 'Tonga', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('222', 'TR', 'Turkey', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('223', 'TT', 'Trinidad and Tobago', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('224', 'TV', 'Tuvalu', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('225', 'TW', 'Taiwan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('226', 'TZ', 'Tanzania', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('227', 'UA', 'Ukraine', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('228', 'UG', 'Uganda', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('229', 'UM', 'United States Minor Outlying Islands', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('230', 'US', 'United States of America', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('231', 'UY', 'Uruguay', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('232', 'UZ', 'Uzbekistan', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('233', 'VA', 'Vatican City', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('234', 'VC', 'Saint Vincent and the Grenadines', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('235', 'VE', 'Venezuela', 'SA');
INSERT INTO esgf_dashboard.country VALUES ('236', 'VG', 'Virgin Islands, British', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('237', 'VI', 'Virgin Islands, U.S.', 'NA');
INSERT INTO esgf_dashboard.country VALUES ('238', 'VN', 'Vietnam', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('239', 'VU', 'Vanuatu', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('240', 'WF', 'Wallis and Futuna Islands', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('241', 'WS', 'Samoa', 'OC');
INSERT INTO esgf_dashboard.country VALUES ('242', 'YE', 'Yemen', 'AS');
INSERT INTO esgf_dashboard.country VALUES ('243', 'YT', 'Mayotte', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('244', 'ZA', 'South Africa', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('245', 'ZM', 'Zambia', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('246', 'ZW', 'Zimbabwe', 'AF');
INSERT INTO esgf_dashboard.country VALUES ('247', 'EU', 'No country', 'EU');
INSERT INTO esgf_dashboard.country VALUES ('248', 'AP', 'No country', 'AS');


/**
 * dashboard_queue table
 **/
DROP TABLE IF EXISTS esgf_dashboard.dashboard_queue;

CREATE TABLE esgf_dashboard.dashboard_queue (
    id bigint PRIMARY KEY,
    url_path character varying NOT NULL,
    remote_addr character varying NOT NULL,
    user_id_hash character varying,
    user_idp character varying,
    service_type character varying,
    success boolean,
    duration double precision,
    size bigint DEFAULT (-1),
    "timestamp" double precision NOT NULL,
    processed smallint DEFAULT 0 NOT NULL
);

ALTER TABLE esgf_dashboard.dashboard_queue OWNER TO dbsuper;


/**
 * Project-specific tables
 **/

/* CMIP5 DROP INSTRUCTIONS */
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_geolocation CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_date CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_dataset CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_time_frequency CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_bridge_time_frequency CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_variable CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_bridge_variable CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_experiment CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_bridge_experiment CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_model CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_bridge_model CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_realm CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_bridge_realm CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dim_institute CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_bridge_institute CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_fact_download CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dmart_clients_time_geolocation CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dmart_model_host_time CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dmart_experiment_host_time CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dmart_variable_host_time CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cmip5_dmart_dataset_host_time CASCADE;

/* CMIP5 DIMENSION TABLES */
CREATE TABLE esgf_dashboard.cmip5_dim_geolocation (
   geolocation_key bigserial PRIMARY KEY,
   latitude numeric(14,11),
   longitude numeric(14,11),
   country_id integer NOT NULL REFERENCES esgf_dashboard.country
);
ALTER TABLE esgf_dashboard.cmip5_dim_geolocation OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_date (
   date_key serial PRIMARY KEY,
   download_date date,
   month smallint,
   year smallint
);
ALTER TABLE esgf_dashboard.cmip5_dim_date OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_dataset (
   dataset_key bigserial PRIMARY KEY,
   dataset_name character varying(64),
   dataset_version smallint,
   datetime_start character varying(64),
   datetime_stop character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dim_dataset OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_time_frequency (
   time_frequency_key serial PRIMARY KEY,
   time_frequency_value character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dim_time_frequency OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_bridge_time_frequency (
   time_frequency_key integer NOT NULL REFERENCES esgf_dashboard.cmip5_dim_time_frequency,
   time_frequency_group_key integer NOT NULL
);
ALTER TABLE esgf_dashboard.cmip5_bridge_time_frequency OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_variable (
   variable_key serial PRIMARY KEY,
   variable_code character varying(64),
   variable_long_name character varying(64),
   cf_standard_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dim_variable OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_bridge_variable (
   variable_key integer NOT NULL REFERENCES esgf_dashboard.cmip5_dim_variable,
   variable_group_key integer NOT NULL
);
ALTER TABLE esgf_dashboard.cmip5_bridge_variable OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_experiment (
   experiment_key serial PRIMARY KEY,
   experiment_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dim_experiment OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_bridge_experiment (
   experiment_key integer NOT NULL REFERENCES esgf_dashboard.cmip5_dim_experiment,
   experiment_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.cmip5_bridge_experiment OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_model (
   model_key serial PRIMARY KEY,
   model_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dim_model OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_bridge_model (
   model_key integer NOT NULL REFERENCES esgf_dashboard.cmip5_dim_model,
   model_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.cmip5_bridge_model OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_realm (
   realm_key serial PRIMARY KEY,
   realm_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dim_realm OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_bridge_realm (
   realm_key integer NOT NULL REFERENCES esgf_dashboard.cmip5_dim_realm,
   realm_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.cmip5_bridge_realm OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dim_institute (
   institute_key serial PRIMARY KEY,
   institute_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dim_institute OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_bridge_institute (
   institute_key integer NOT NULL REFERENCES esgf_dashboard.cmip5_dim_institute,
   institute_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.cmip5_bridge_institute OWNER TO dbsuper;

/* CMIP5 FACT TABLE */
CREATE TABLE esgf_dashboard.cmip5_fact_download (
   download_key bigserial PRIMARY KEY,
   size bigint,
   success boolean,
   duration integer,
   replica boolean,
   host_name character varying,
   hour smallint,
   minute smallint,
   user_id_hash character varying,
   user_idp character varying,
   date_key integer REFERENCES esgf_dashboard.cmip5_dim_date,
   geolocation_key bigint REFERENCES esgf_dashboard.cmip5_dim_geolocation,
   dataset_key bigint REFERENCES esgf_dashboard.cmip5_dim_dataset,
   time_frequency_group_key integer,
   variable_group_key integer,
   experiment_group_key integer,
   model_group_key integer,
   realm_group_key integer,
   institute_group_key integer,
   id_query integer
);
ALTER TABLE esgf_dashboard.cmip5_fact_download OWNER TO dbsuper;

/* CMIP5 DATA MARTS */
CREATE TABLE esgf_dashboard.cmip5_dmart_clients_time_geolocation (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   number_of_replica_downloads bigint,
   month smallint,
   year smallint,
   latitude numeric(14,11),
   longitude numeric(14,11),
   host_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dmart_clients_time_geolocation OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dmart_model_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   number_of_replica_downloads bigint,
   month smallint,
   year smallint,
   host_name character varying(64),
   model_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dmart_model_host_time OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dmart_experiment_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   number_of_replica_downloads bigint,
   month smallint,
   year smallint,
   host_name character varying(64),
   experiment_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dmart_experiment_host_time OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dmart_variable_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   number_of_replica_downloads bigint,
   month smallint,
   year smallint,
   host_name character varying(64),
   variable_code character varying(64),
   variable_long_name character varying(64),
   cf_standard_name character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dmart_variable_host_time OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cmip5_dmart_dataset_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   number_of_replica_downloads bigint,
   month smallint,
   year smallint,
   host_name character varying(64),
   dataset_name character varying(64),
   dataset_version smallint,
   datetime_start character varying(64),
   datetime_stop character varying(64)
);
ALTER TABLE esgf_dashboard.cmip5_dmart_dataset_host_time OWNER TO dbsuper;


/* OBS4MIPS DROP INSTRUCTIONS */
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_geolocation CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_date CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_dataset CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_file CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_institute CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_bridge_institute CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_variable CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_bridge_variable CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_time_frequency CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_bridge_time_frequency CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_processing_level CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_bridge_processing_level CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_source_id CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_bridge_source_id CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dim_realm CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_bridge_realm CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_fact_download CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dmart_clients_time_geolocation CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dmart_variable_host_time CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dmart_source_host_time CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dmart_realm_host_time CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.obs4mips_dmart_dataset_host_time CASCADE;

/* OBS4MIPS DIMENSION TABLES */
CREATE TABLE esgf_dashboard.obs4mips_dim_geolocation (
   geolocation_key bigserial PRIMARY KEY,
   latitude numeric(14,11),
   longitude numeric(14,11),
   country_id integer NOT NULL REFERENCES esgf_dashboard.country
);
ALTER TABLE esgf_dashboard.obs4mips_dim_geolocation OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_date (
   date_key serial PRIMARY KEY,
   download_date date,
   month smallint,
   year smallint
);
ALTER TABLE esgf_dashboard.obs4mips_dim_date OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_dataset (
   dataset_key bigserial PRIMARY KEY,
   dataset_name character varying(64),
   dataset_version smallint,
   datetime_start character varying(64),
   datetime_stop character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dim_dataset OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_file (
   file_key bigserial PRIMARY KEY,
   file_name character varying(64),
   file_size bigint
);
ALTER TABLE esgf_dashboard.obs4mips_dim_file OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_institute (
   institute_key serial PRIMARY KEY,
   institute_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dim_institute OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_bridge_institute (
   institute_key integer NOT NULL REFERENCES esgf_dashboard.obs4mips_dim_institute,
   institute_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.obs4mips_bridge_institute OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_variable (
   variable_key serial PRIMARY KEY,
   variable_code character varying(64),
   variable_long_name character varying(64),
   cf_standard_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dim_variable OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_bridge_variable (
   variable_key integer NOT NULL REFERENCES esgf_dashboard.obs4mips_dim_variable,
   variable_group_key integer NOT NULL
);
ALTER TABLE esgf_dashboard.obs4mips_bridge_variable OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_time_frequency (
   time_frequency_key serial PRIMARY KEY,
   time_frequency_value character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dim_time_frequency OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_bridge_time_frequency (
   time_frequency_key integer NOT NULL REFERENCES esgf_dashboard.obs4mips_dim_time_frequency,
   time_frequency_group_key integer NOT NULL
);
ALTER TABLE esgf_dashboard.obs4mips_bridge_time_frequency OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_processing_level (
   processing_level_key serial PRIMARY KEY,
   processing_level_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dim_processing_level OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_bridge_processing_level (
   processing_level_key integer NOT NULL REFERENCES esgf_dashboard.obs4mips_dim_processing_level,
   processing_level_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.obs4mips_bridge_processing_level OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_source_id (
   source_id_key serial PRIMARY KEY,
   source_id_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dim_source_id OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_bridge_source_id (
   source_id_key integer NOT NULL REFERENCES esgf_dashboard.obs4mips_dim_source_id,
   source_id_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.obs4mips_bridge_source_id OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dim_realm (
   realm_key serial PRIMARY KEY,
   realm_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dim_realm OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_bridge_realm (
   realm_key integer NOT NULL REFERENCES esgf_dashboard.obs4mips_dim_realm,
   realm_group_key smallint NOT NULL
);
ALTER TABLE esgf_dashboard.obs4mips_bridge_realm OWNER TO dbsuper;

/* OBS4MIPS FACT TABLE */
CREATE TABLE esgf_dashboard.obs4mips_fact_download (
   download_key bigserial PRIMARY KEY,
   size bigint,
   success boolean,
   duration integer,
   user_id_hash character varying,
   user_idp character varying,
   host_name character varying,
   hour smallint,
   minute smallint,
   index_node_name character varying(64),
   dataset_key bigint REFERENCES esgf_dashboard.obs4mips_dim_dataset,
   file_key bigint REFERENCES esgf_dashboard.obs4mips_dim_file,
   geolocation_key bigint REFERENCES esgf_dashboard.obs4mips_dim_geolocation,
   date_key integer REFERENCES esgf_dashboard.obs4mips_dim_date,
   institute_group_key integer,
   variable_group_key integer,
   time_frequency_group_key integer,
   processing_level_group_key integer,
   source_id_group_key integer,
   realm_group_key integer,
   id_query integer
);
ALTER TABLE esgf_dashboard.obs4mips_fact_download OWNER TO dbsuper;

/* OBS4MIPS DATA MARTS */
CREATE TABLE esgf_dashboard.obs4mips_dmart_clients_time_geolocation (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   month smallint,
   year smallint,
   latitude numeric(14,11),
   longitude numeric(14,11),
   host_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dmart_clients_time_geolocation OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dmart_variable_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   month smallint,
   year smallint,
   host_name character varying(64),
   variable_code character varying(64),
   variable_long_name character varying(64),
   cf_standard_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dmart_variable_host_time OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dmart_source_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   month smallint,
   year smallint,
   host_name character varying(64),
   source_id_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dmart_source_host_time OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dmart_realm_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   month smallint,
   year smallint,
   host_name character varying(64),
   realm_name character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dmart_realm_host_time OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.obs4mips_dmart_dataset_host_time (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   average_duration integer,
   number_of_users integer,
   month smallint,
   year smallint,
   host_name character varying(64),
   dataset_name character varying(64),
   dataset_version smallint,
   datetime_start character varying(64),
   datetime_stop character varying(64)
);
ALTER TABLE esgf_dashboard.obs4mips_dmart_dataset_host_time OWNER TO dbsuper;


/**
* Cross-project tables
**/

/* CROSS-PROJECT DROP INSTRUCTIONS */
DROP TABLE IF EXISTS esgf_dashboard.cross_dmart_project_host CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cross_fact_download CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cross_dim_date CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cross_dim_geolocation CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cross_bridge_project CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cross_dim_project CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cross_dmart_project_host_time CASCADE;
DROP TABLE IF EXISTS esgf_dashboard.cross_dmart_project_host_geolocation CASCADE;

/* CROSS-PROJECT DIMENSIONS */
CREATE TABLE esgf_dashboard.cross_dim_date (
    date_key serial PRIMARY KEY,
    download_date date,
    month smallint,
    year smallint
);
ALTER TABLE esgf_dashboard.cross_dim_date OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cross_dim_geolocation (
    geolocation_key bigserial PRIMARY KEY,
    latitude numeric(14,11),
    longitude numeric(14,11),
    country_id integer NOT NULL REFERENCES esgf_dashboard.country
);
ALTER TABLE esgf_dashboard.cross_dim_geolocation OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cross_dim_project (
    project_key serial PRIMARY KEY,
    project_name character varying(64)
);
ALTER TABLE esgf_dashboard.cross_dim_project OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cross_bridge_project (
    project_key integer NOT NULL REFERENCES esgf_dashboard.cross_dim_project,
    project_group_key integer NOT NULL
);
ALTER TABLE esgf_dashboard.cross_bridge_project OWNER TO dbsuper;

/* CROSS-PROJECT FACT TABLE */
CREATE TABLE esgf_dashboard.cross_fact_download (
    download_key bigserial PRIMARY KEY,
    size bigint,
    success boolean,
    duration integer,
    replica boolean,
    user_id_hash character varying(64),
    host_name character varying(64),
    user_idp character varying(64),
    hour smallint,
    minute smallint,
    project_group_key integer,
    geolocation_key bigint REFERENCES esgf_dashboard.cross_dim_geolocation,
    date_key integer REFERENCES esgf_dashboard.cross_dim_date,
    id_query integer
);
ALTER TABLE esgf_dashboard.cross_fact_download OWNER TO dbsuper;

/* CROSS-PROJECT DATA MARTS */
CREATE TABLE esgf_dashboard.cross_dmart_project_host_time (
    dmart_key bigserial PRIMARY KEY,
    total_size bigint,
    number_of_downloads bigint,
    number_of_successful_downloads bigint,
    number_of_replica_downloads bigint,
    average_duration integer,
    number_of_users integer,
    host_name character varying(64),
    project_name character varying(64),
    month smallint,
    year smallint
);
ALTER TABLE esgf_dashboard.cross_dmart_project_host_time OWNER TO dbsuper;

CREATE TABLE esgf_dashboard.cross_dmart_project_host_geolocation (
   dmart_key bigserial PRIMARY KEY,
   total_size bigint,
   number_of_downloads bigint,
   number_of_successful_downloads bigint,
   number_of_replica_downloads bigint,
   average_duration integer,
   number_of_users integer,
   host_name character varying(64),
   project_name character varying(64),
   latitude numeric(14,11),
   longitude numeric(14,11)
);
ALTER TABLE esgf_dashboard.cross_dmart_project_host_geolocation OWNER TO dbsuper;

DROP TABLE IF EXISTS esgf_dashboard.registry;
CREATE TABLE esgf_dashboard.registry (
  datmart character varying(128) PRIMARY KEY,
  dmart_key integer default 0,
  timestamp integer
);
insert into esgf_dashboard.registry values('esgf_dashboard.cross_dmart_project_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.cross_dmart_project_host_geolocation',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.obs4mips_dmart_clients_host_time_geolocation',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.obs4mips_dmart_variable_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.obs4mips_dmart_source_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.obs4mips_dmart_realm_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.obs4mips_dmart_dataset_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.cmip5_dmart_clients_host_time_geolocation',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.cmip5_dmart_experiment_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.cmip5_dmart_model_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.cmip5_dmart_variable_host_time',0,0);
insert into esgf_dashboard.registry values('esgf_dashboard.cmip5_dmart_dataset_host_time',0,0);


--
-- Drop the functions used for updating the dashboard_queue;
--
drop function if exists store_dashboard_queue() CASCADE;
drop function if exists update_dashboard_queue() CASCADE;
drop function if exists delete_dashboard_queue() CASCADE;
drop function if exists update_url(integer);
drop LANGUAGE if exists plpgsql;

--
--Copy the rows of the access_logging table into the dashboard_queue table
--

insert into esgf_dashboard.dashboard_queue(id, url_path, remote_addr,user_id_hash, user_idp, service_type, success, duration, size, timestamp) select id, url, remote_addr, user_id_hash, user_idp, service_type, success, duration, data_size, date_fetched from esgf_node_manager.access_logging;

update esgf_dashboard.dashboard_queue set processed=1 where timestamp<1488326400;

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = esgf_dashboard, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Function to update the urls in the dashboard_queue table
--

CREATE LANGUAGE plpgsql;
create function update_url(integer)
returns integer as'
declare
i alias for $1;
j integer:=28+i;
begin
UPDATE esgf_dashboard.dashboard_queue SET url_path = substr(url_path,
j) where url_path like ''http%'';
return 0;
end;
'language 'plpgsql';

--
-- Insert into the dashboard_queue_table a new row stored in the access_logging table
--

CREATE FUNCTION store_dashboard_queue() RETURNS trigger AS
$store_new_entry$
declare
BEGIN
-- Update dashboard_queue table
if NEW.date_fetched>=1488326400 then
insert into esgf_dashboard.dashboard_queue(id, url_path, remote_addr,
user_id_hash, user_idp, service_type, success, duration, size,
timestamp)values(NEW.id, NEW.url, NEW.remote_addr, NEW.user_id_hash,
NEW.user_idp, NEW.service_type, NEW.success, NEW.duration,
NEW.data_size, NEW.date_fetched);
else
insert into esgf_dashboard.dashboard_queue(id, url_path, remote_addr,
user_id_hash, user_idp, service_type, success, duration, size,
timestamp,processed)values(NEW.id, NEW.url, NEW.remote_addr, NEW.user_id_hash,
NEW.user_idp, NEW.service_type, NEW.success, NEW.duration,
NEW.data_size, NEW.date_fetched,1);
end if;
RETURN NEW;
END
$store_new_entry$ LANGUAGE plpgsql;


CREATE FUNCTION update_dashboard_queue() RETURNS trigger AS
$store_update_entry$
declare
url_http varchar;
BEGIN
-- Update dashboard_queue table
update esgf_dashboard.dashboard_queue set success=NEW.success, size=NEW.data_size, duration=NEW.duration WHERE id = OLD.id;
url_http:=url_path from esgf_dashboard.dashboard_queue WHERE id = OLD.id;
if strpos(url_http,'http')<>0 then
update esgf_dashboard.dashboard_queue set url_path=subquery.url_res
FROM (select file.url as url_res from public.file_version as file,
esgf_dashboard.dashboard_queue as log where log.url_path like '%'||file.url
and log.url_path=url_http) as subquery where url_path=url_http and id=OLD.id;
end if;
RETURN NEW;
END
$store_update_entry$ LANGUAGE plpgsql;

CREATE FUNCTION delete_dashboard_queue() RETURNS trigger AS
$store_delete_entry$
declare
BEGIN
-- Update dashboard_queue table
delete from esgf_dashboard.dashboard_queue where id=OLD.id;
RETURN NEW;
END
$store_delete_entry$ LANGUAGE plpgsql;

CREATE TRIGGER store_new_entry
AFTER INSERT ON
esgf_node_manager.access_logging
FOR EACH ROW EXECUTE PROCEDURE store_dashboard_queue();
CREATE TRIGGER store_update_entry
AFTER UPDATE ON
esgf_node_manager.access_logging
FOR EACH ROW EXECUTE PROCEDURE update_dashboard_queue();
CREATE TRIGGER store_delete_entry
AFTER DELETE ON
esgf_node_manager.access_logging
FOR EACH ROW EXECUTE PROCEDURE delete_dashboard_queue();
--
-- Update the urls in the dashboard_queue_table
-- Note: FQDN=0 will truncate no URL
--
set search_path=esgf_dashboard;
select update_url(0);
