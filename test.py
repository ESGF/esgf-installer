import argparse
import logging
import os

from installer.director import Director

def main():
    log_name = os.path.join("logs", "sample.log")
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
    parser.add_argument("-f", "--freeze", action="store_true")
    parser.add_argument("-t", "--type", nargs="+", required=False)

    director = Director(parser.parse_args())
    director.pre_check()
    director.begin()

if __name__ == "__main__":
    main()
