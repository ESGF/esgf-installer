import argparse
import ConfigParser
import logging
import os
import sys

import psycopg2

def main():

    parser = argparse.ArgumentParser(
        description="A script for querying the esgcet database for an OpenID, given a username"
    )
    parser.add_argument("username",  help="The username for which to query for the OpenID")
    args = parser.parse_args()

    try:
        esgf_home = os.environ["ESGF_HOME"]
    except KeyError:
        esgf_home = os.path.join(os.sep, "esg")

    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.DEBUG,
        filename=os.path.join(esgf_home, "config", "myproxy", "mapapp.og"),
        maxBytes=2*1024*1024
    )
    properties_file = os.path.join(esgf_home, "config", "esgf.properties")

    config_parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    config_parser.read(properties_file)

    section = "installer.properties"

    db = config_parser.get(section, "db.database")
    host = config_parser.get(section, "db.host")
    port = config_parser.get(section, "db.port")
    user = config_parser.get(section, "db.user")
    esgf_host = config_parser.get(section, "esgf.host")
    gateway = "https://{}/esgf-idp/openid/%".format(esgf_host)

    pass_file = os.path.join(esgf_home, "config", ".esg_pg_pass")
    with open(pass_file, "rb") as filep:
        password = filep.read().strip()

    cs = "dbname=%s user=%s password=%s host=%s port=%s" % (db, user, password, host, port)
    conn = psycopg2.connect(cs)
    cur = conn.cursor()
    query = "SELECT DISTINCT openid FROM esgf_security.user"
    query += " WHERE username=%(username)s AND openid LIKE %(gateway)s "
    values = {
        "username": args.username,
        "gateway": gateway
    }
    cur.execute(query, values)
    result = cur.fetchone()
    if not result:
        output = "No OpenID found for {}".format(args.username)
        output += "\ndbname=%s user=%s host=%s port=%s\n" % (db, user, host, port)
        output += query % values
        print output
        logging.error(output)
        sys.exit(1)
    logging.info("Success %s", result[0])
    print result[0]

main()
