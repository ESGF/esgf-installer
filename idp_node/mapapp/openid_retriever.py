import argparse
import ConfigParser
import logging
import os
import sys

import OpenSSL
import psycopg2

def get_openid(args, config_parser, esgf_home):

    pass_file = os.path.join(esgf_home, "config", ".esg_pg_pass")
    with open(pass_file, "rb") as filep:
        password = filep.read().strip()

    section = "installer.properties"

    db = config_parser.get(section, "db.database")
    host = config_parser.get(section, "db.host")
    port = config_parser.get(section, "db.port")
    user = config_parser.get(section, "db.user")
    esgf_host = config_parser.get(section, "esgf.host")
    gateway = "https://{}/esgf-idp/openid/%".format(esgf_host)

    cs = "dbname=%s user=%s password=%s host=%s port=%s" % (db, user, password, host, port)
    cs_no_pass = "dbname=%s user=%s host=%s port=%s" % (db, user, host, port)
    logging.info(cs_no_pass)
    conn = psycopg2.connect(cs)
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

    with open(args.cert_file) as cert:
        cert_contents = cert.read()
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_contents)
    return cert.get_subject()

def main():

    parser = argparse.ArgumentParser(
        description="A script for querying the esgcet database for an OpenID, given a username"
    )
    parser.add_argument("username",  help="The username for which to query for the OpenID")
    parser.add_argument("cert_file",  help="The username for which to query for the OpenID")
    args = parser.parse_args()

    try:
        esgf_home = os.environ["ESGF_HOME"]
    except KeyError:
        esgf_home = os.path.join(os.sep, "esg")

    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.DEBUG,
        filename=os.path.join(esgf_home, "config", "myproxy", "mapapp.log"),
        maxBytes=2*1024*1024
    )
    properties_file = os.path.join(esgf_home, "config", "esgf.properties")

    config_parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    config_parser.read(properties_file)

    openid = get_openid(args, config_parser, esgf_home)
    subject_line = get_subject_line(args)
    output = "/O={}/OU={}/CN={}"
    output = output.format(
        subject_line.O,
        subject_line.OU,
        openid
    )
    print output
    logging.info("Sent to myproxy: %s", output)

main()
