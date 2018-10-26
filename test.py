import argparse
import logging
import os

from installer.director import Director
from installer.utils import mkdir_p

def main():
    log_dir = "logs"
    mkdir_p(log_dir)
    log_name = os.path.join(log_dir, "sample.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] [%(levelname)-5.5s]  %(message)s",
        handlers=[
            logging.FileHandler(log_name),
            logging.StreamHandler()
        ]
    )
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

if __name__ == "__main__":
    main()
