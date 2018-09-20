import argparse

from installer.director import Director

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--install", nargs="*", required=False)
    parser.add_argument("-t", "--type", nargs="+", required=False)

    director = Director(parser.parse_args())
    director.pre_check()
    director.begin()

if __name__ == "__main__":
    main()
