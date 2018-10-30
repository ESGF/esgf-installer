import argparse
import logging
import os

from installer.director import Director
from installer.utils import mkdir_p


def main():

    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--install", nargs="*", required=False)
    parser.add_argument("-u", "--uninstall", nargs="*", required=False)
    parser.add_argument("--start", nargs="*", required=False)
    parser.add_argument("--stop", nargs="*", required=False)
    parser.add_argument("--restart", nargs="*", required=False)
    parser.add_argument("-f", "--freeze", action="store_true")
    parser.add_argument("-t", "--type", nargs="+", required=False)
    parser.add_argument("-p", "--params", dest="input_params", default="params.ini")

    director = Director(parser.parse_args())
    director.pre_check()
    director.begin()

def setup_logging():
    log_name = "sample.log"
    log_form = "%(asctime)s [%(name)s] [%(levelname)s]  %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_form,
        filename=log_name,
        filemode='w'
    )
    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    formatter = logging.Formatter("[%(name)s] [%(levelname)s]  %(message)s")
    ch.setFormatter(formatter)
    log.addHandler(ch)


if __name__ == "__main__":
    main()
