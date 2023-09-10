from .util import get_loc_stats

def main() -> None:
    print(get_loc_stats("https://github.com/eggplants/getjump", "master"))

if __name__ == "__main__":
    main()
