'''
Build the strings for myproxy-server to use in myproxy-logon,
See http://grid.ncsa.illinois.edu/myproxy/man/myproxy-server.config.5.html
'''
import argparse
import ConfigParser
import logging
import os
import sys

import OpenSSL
import psycopg2

def db_connection(config_parser, esgf_home):
    pass_file = os.path.join(esgf_home, "config", ".esg_pg_pass")
    logging.info("Retrieving pg pass from %s", pass_file)
    with open(pass_file, "rb") as filep:
        password = filep.read().strip()

    section = "installer.properties"
    db = config_parser.get(section, "db.database")
    host = config_parser.get(section, "db.host")
    port = config_parser.get(section, "db.port")
    user = config_parser.get(section, "db.user")

    connection_params = (
        "dbname=%s user=%s password=%s host=%s port=%s" %
        (db, user, password, host, port)
    )
    connection_params_no_pass = (
        "dbname=%s user=%s host=%s port=%s" %
        (db, user, host, port)
    )
    logging.info(connection_params_no_pass)

    return psycopg2.connect(connection_params)

def build_grouprole(args, config_parser, esgf_home):
    ''' Build the group and role string for a specified username '''
    logging.info("Fetching groups and roles for %s", args.username)

    section = "installer.properties"
    esgf_host = config_parser.get(section, "esgf.host")
    gateway = "https://{}/esgf-idp/openid/%".format(esgf_host)

    conn = db_connection(config_parser, esgf_home)
    cur = conn.cursor()

    query = " SELECT g.name, r.name"
    query += " FROM esgf_security.group AS g, esgf_security.role AS r,"
    query += " esgf_security.permission AS p, esgf_security.user AS u"
    query += " WHERE p.user_id=u.id"
    query += " AND u.username=%(username)s"
    query += " AND u.openid LIKE %(gateway)s"
    query += " AND p.group_id=g.id"
    query += " AND p.role_id=r.id"
    values = {
        "username": args.username,
        "gateway": gateway
    }
    logging.info(query, values)
    cur.execute(query, values)
    result = cur.fetchall()
    #         //         group     | role
    #         //    ----------------+------
    #         //    CMIP5 Research | User
    #         //    NASA OBS       | User
    #         //    ORNL OBS       | User
    if not result:
        return None
    grouprole_elements = []
    for group, role in result:
        grouprole_elements.append("group_" + group + "_role_" + role)
    return ";".join(grouprole_elements)

def get_openid(args, config_parser, esgf_home):
    ''' Retrieve the OpenID for a specified username '''
    logging.info("Fetching OpenID for %s", args.username)

    section = "installer.properties"
    esgf_host = config_parser.get(section, "esgf.host")
    gateway = "https://{}/esgf-idp/openid/%".format(esgf_host)

    conn = db_connection(config_parser, esgf_home)
    cur = conn.cursor()
    query = "SELECT DISTINCT openid FROM esgf_security.user"
    query += " WHERE username=%(username)s AND openid LIKE %(gateway)s "
    values = {
        "username": args.username,
        "gateway": gateway
    }
    logging.info(query, values)
    cur.execute(query, values)
    result = cur.fetchone()
    if not result:
        output = "No OpenID found for {}".format(args.username)
        print output
        logging.error(output)
        sys.exit(1)
    logging.info("OpenID Success: %s", result[0])
    return result[0]

def get_subject_line(args):
    ''' Retrieve the subject line from the specified certificate file '''
    logging.info("Loading cert file: %s", args.cert_file)
    with open(args.cert_file) as cert:
        cert_contents = cert.read()
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_contents)
    return cert.get_subject()

def main():
    '''
    Parse arguments, setup logging, retrieve properties,
    call needed functions and write new subject line to stdout
    '''
    parser = argparse.ArgumentParser(
        description="A script for building strings to be used by myproxy-logon"
    )
    parser.add_argument("username", help="The username for which to query for the OpenID")
    parser.add_argument("--cert_file", help="The path to cert file to read the subject line from")
    parser.add_argument(
        "--mapapp",
        action="store_true",
        help="A flag to indicate to output subject line and openid"
    )
    parser.add_argument(
        "--extapp",
        action="store_true",
        help="A flag to indicate to output attributes and groupid"
    )
    args = parser.parse_args()

    try:
        esgf_home = os.environ["ESGF_HOME"]
    except KeyError:
        esgf_home = os.path.join(os.sep, "esg")

    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.DEBUG,
        filename=os.path.join(esgf_home, "config", "myproxy", "app.log"),
        maxBytes=2*1024*1024
    )
    properties_file = os.path.join(esgf_home, "config", "esgf.properties")

    config_parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    config_parser.read(properties_file)

    if args.mapapp:
        openid = get_openid(args, config_parser, esgf_home)
        subject_line = get_subject_line(args)
        output = "/O={}/OU={}/CN={}"
        output = output.format(
            subject_line.O,
            subject_line.OU,
            openid
        )
        print output
        logging.info("Mapapp sent to myproxy: %s", output)
    elif args.extapp:
        grouprole = build_grouprole(args, config_parser, esgf_home)
        if grouprole is not None:
            grouprole = "esg.vo.group.roles={}".format(grouprole)
        else:
            grouprole = "null"
        openid = get_openid(args, config_parser, esgf_home)
        #1.2.3.4.4.3.2.1.7.8=ASN1:UTF8String:null:esg.vo.openid=https://esgf-dev1.llnl.gov/esgf-idp/openid/ncarlson
        output = "1.2.3.4.4.3.2.1.7.8=ASN1:UTF8String:{}:esg.vo.openid={}"
        output = output.format(grouprole, openid)
        print output
        logging.info("Extapp sent to myproxy: %s", output)

main()
