import pandas as pd


def main():
    rotpot_db = pd.read_csv("rotpot_db.csv")
    splus_name = "splus_name"
    discord_name = "discord_name"
    new_discord_name = "new_discord_name"
    df: pd.DataFrame = rotpot_db.iloc[:, :3]
    new_discord_names = rotpot_db.iloc[:, 3:].set_index(new_discord_name)
    with open("splus_names", "r") as f:
        splus_names = pd.DataFrame(
            pd.Series(eval(f.read()), name=splus_name)
        ).set_index(splus_name)
    df = df.set_index(splus_name).join(splus_names, how="outer", rsuffix="new")
    df = df.reset_index()
    df = df.set_index(discord_name).join(new_discord_names, how="outer")
    df["discord_name"] = df.index
    print(df.to_string(index=False))
    df.to_csv("rotbot_db_updated.csv")


if __name__ == "__main__":
    main()
