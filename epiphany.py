import json
import logging
import math
import matplotlib.pyplot as plt
import os
import pandas as pd
import re
import requests
import seaborn as sns
from unidecode import unidecode

# Functions for processing tournament data

hb="haas-bioroid"
nbn="nbn"
jinteki="jinteki"
weyland="weyland-consortium"

anarch="anarch"
shaper="shaper"
criminal="criminal"

def faction_hues():
    return {
        "shaper": "limegreen",
        "criminal": "royalblue",
        "anarch": "orangered",
        "adam": "gold",
        "jinteki": "crimson",
        "nbn": "darkorange",
        "haas-bioroid": "blueviolet",
        "weyland-consortium": "darkgreen",
    }


mojibake = {
    "EsÃ¢ Afontov: Eco-Insurrectionist" : "Esâ Afontov: Eco-Insurrectionist",
    "TÄ�o Salonga: Telepresence Magician" : "René \"Loup\" Arcemont: Party Animal"
}

tai_members = ["Baa Ram Wu", "AugustusCaesar", "HaverOfFun", "xdg", "aksu", "Gathzen", "Jai", "rubenpieters", "profwacko"]

def is_tai(player):
    return player in tai_members

def tai_matches(row):
    return is_tai(row.corp_player) or is_tai(row.runner_player)

def tai_corp_matches(row):
    return is_tai(row.corp_player)

def tai_runner_matches(row):
    return is_tai(row.runner_player)

def normalize_title(title):
    # Remove accents and convert to lowercase
    return unidecode(title).lower()

def get_cobra_json_from_url(tid: str):
    r = requests.request(url=f"https://cobr.ai/tournaments/{tid}.json", method="GET")
    raw_data = r.json()
    return raw_data

def new_dataframe_from_template(tmpl) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype=t) for c, t in tmpl.items()})

def new_dataframe_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    tmpl = df.dtypes.to_dict()
    return new_dataframe_from_template(tmpl)

def get_json_from_file(file_path: str):
    raw_data = {}
    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    return raw_data

def get_short_title(name: str):
    pattern = r"(.+): (.+)"

    match = re.match(pattern, name)
    if match:
        # Extract the matched parts
        before = match.group(1)
        after = match.group(2)

        if before in ["Haas-Bioroid", "Jinteki", "NBN", "Weyland Consortium"]:
            return after

        return before
    else:
        assert false, f"Couldn't parse ID name {name}"

def get_id_data_from_file(file_path: str) -> pd.DataFrame:
    raw_data = get_json_from_file(file_path)
    cards_df = pd.DataFrame(raw_data["data"])
    id_df = (
        cards_df[cards_df["type_code"] == "identity"]
        .groupby(["title", "faction_code"])
        .size()
        .reset_index()[["title", "faction_code"]]
    )
    id_df["title_ascii"] = id_df["title"].apply(normalize_title)
    id_df["short_title"] = id_df["title"].apply(get_short_title)

    return id_df

def get_tournament_players(id_df, raw_data, abr_claims_data):
    players = pd.DataFrame(raw_data["players"])

    players["corpIdentity"].fillna("Unknown", inplace=True)
    players["runnerIdentity"].fillna("Unknown", inplace=True)

    players["corpIdentity_ascii"]=players["corpIdentity"].apply(normalize_title)
    players["runnerIdentity_ascii"]=players["runnerIdentity"].apply(normalize_title)

    players.drop(["corpIdentity","runnerIdentity"], axis=1, inplace=True)

    players = pd.merge(
        players, id_df, how="left", left_on="corpIdentity_ascii", right_on="title_ascii"
    ).rename(columns={"faction_code": "corpFaction", "short_title": "corpIdentity"})
    players = pd.merge(
        players, id_df, how="left", left_on="runnerIdentity_ascii", right_on="title_ascii"
    ).rename(columns={"faction_code": "runnerFaction", "short_title": "runnerIdentity"})

    claims = pd.DataFrame(abr_claims_data)

    players = pd.merge(
        players,
        claims[["user_import_name", "user_name"]],
        how="left",
        left_on="name",
        right_on="user_import_name",
    ).rename(columns={"user_import_name":"tournamentName", "user_name":"abrName"})

    players["name"] = players["abrName"].fillna(players["name"])

    return players[[
        "id", "name", "rank", "corpIdentity", "corpFaction", "runnerIdentity", "runnerFaction", "tournamentName", "abrName",
    ]]

# aggregate_tournament_data takes a dataframe with the output of
# get_id_data_from_file and an array of tournaments.  It returns dataframes
# with flattened match records and paired match records over the entire set.
#
# Input elements of the tournament list should be an array with the prefix of a
# file under 'data/', omitting the "-aesops.json", "-cobra.json", or
# "-abr.json" part, a string "cobra" or "aesops" indicating the source of the
# data.
#
# ["2024-01-06-online-new-years-co", "aesops"]
def aggregate_tournament_data(id_df, tournaments) -> (pd.DataFrame, pd.DataFrame):
    gamedata_for_event = {}
    abr_for_event = {}
    players_for_event = {}
    flattened_matches_for_event = {}
    paired_matches_for_event = {}

    # extract data for each tournament
    for tt in tournaments:
        t, s = tt
        assert s == "cobra" or s == "aesops", f"unsupported source {source} for {t}"

        gamedata_for_event[t] = get_json_from_file(f"data/{t}-{s}.json")
        abr_for_event[t] = get_json_from_file(f"data/{t}-abr.json")
        p = get_tournament_players(id_df, gamedata_for_event[t], abr_for_event[t])
        players_for_event[t] = p
        flattened_matches_for_event[t] = get_flattened_match_records(
            s, gamedata_for_event[t], p
        )
        paired_matches_for_event[t] = get_paired_match_records(flattened_matches_for_event[t])

    # aggregate over all tournaments
    t0_name = tournaments[0][0]
    agg_flattened_matches = new_dataframe_from_dataframe(flattened_matches_for_event[t0_name])
    agg_paired_matches = new_dataframe_from_dataframe(paired_matches_for_event[t0_name])
    for tt in tournaments:
        t = tt[0]
        agg_flattened_matches = pd.concat([agg_flattened_matches, flattened_matches_for_event[t]], ignore_index=True)
        agg_paired_matches = pd.concat(
            [agg_paired_matches, paired_matches_for_event[t]], ignore_index=True
        )

    return agg_flattened_matches, agg_paired_matches

# in this context, a "match" represents a single player's record in a match. player_fraction
# is the fraction of the swiss ranks that are valid for including player pairings.  The default
# is 1.0 to include all ranks, but zero is also special cased to do the same.
def get_flattened_match_records(source, raw_data, players):
    assert source == "cobra" or source == "aesops", f"unsupported source {source}"
    template = {
        "event": "str",
        "date": "datetime64[ns]",
        "YM": "string",
        "table": "int",
        "round": "int",
        "id": "int",
        "runnerScore": "int",
        "corpScore": "int",
        "combinedScore": "int",
        "intentionalDraw": "bool",
        "twoForOne": "bool",
        "eliminationGame": "bool",
        "runnerWin": "int",
        "corpWin": "int",
        "runnerPlay": "int",
        "corpPlay": "int",
    }
    if source == "cobra":
        return get_flattened_match_records_cobra(raw_data, players, template)

    return get_flattened_match_records_aesops(raw_data, players, template)

def get_flattened_match_records_cobra(raw_data, players, template):
    event_name = raw_data["name"]
    event_date = pd.to_datetime(raw_data["date"])

    records = new_dataframe_from_template(template)

    for rnd, tables in enumerate(raw_data["rounds"]):
        for table_number, table in enumerate(tables):
            # skip byes
            if table["player1"]["id"] is None or table["player2"]["id"] is None:
                continue

            # skip matches with no data; maybe this round/match was not actually playede
            if not table["eliminationGame"] and (
                table["player1"]["runnerScore"] is None
                or table["player1"]["corpScore"] is None
                or table["player2"]["runnerScore"] is None
                or table["player2"]["corpScore"] is None
            ):
                continue 

            # skip swiss matches with no player or corp score; these draws have no runner/corp win info
            if not table["eliminationGame"] and (
                table["player1"]["runnerScore"]
                + table["player1"]["corpScore"]
                + table["player2"]["runnerScore"]
                + table["player2"]["corpScore"]
                == 0
            ):
                continue

            for player in ["player1", "player2"]:
                df = pd.DataFrame([table[player]])
                df["event"] = event_name
                df["date"] = event_date
                df["YM"] = event_date.to_period("M").strftime("%Y-%m")
                df["table"] = table["table"]
                df["round"] = rnd + 1
                df["twoForOne"] = table["twoForOne"]
                df["intentionalDraw"] = table["intentionalDraw"]
                df["eliminationGame"] = table["eliminationGame"]
                records = pd.concat([records, df], ignore_index=True)

    return augment_player_records(records, players)

def get_flattened_match_records_aesops(raw_data, players, template):
    event_name = raw_data["name"]
    event_date = pd.to_datetime(raw_data["date"])

    records = new_dataframe_from_template(template)

    for rnd, tables in enumerate(raw_data["rounds"]):
        for table_number, table in enumerate(tables):
            # skip byes
            if table["runnerPlayer"] == "(BYE)" or table["corpPlayer"] == "(BYE)":
                continue

            # skip swiss matches with no player or corp score; these draws have no runner/corp win info
            if not table.get("eliminationGame") and ( table["runnerScore"] + table["corpScore"] == 0):
                continue

            corp_row = {}
            corp_row["id"] = table["corpPlayer"]
            corp_row["event"] = event_name
            corp_row["date"] = event_date
            corp_row["YM"] = event_date.to_period("M").strftime("%Y-%m")
            corp_row["table"] = table["tableNumber"]
            corp_row["round"] = rnd + 1
            corp_row["twoForOne"] = False
            corp_row["intentionalDraw"] = False # not reported
            corp_row["corpPlay"] = 1
            corp_row["runnerPlay"] = 0
            if table.get("eliminationGame"):
                corp_row["eliminationGame"] = True
                corp_row["runnerScore"] = 0
                corp_row["runnerWin"] = 0
                if table["winner_id"] == table["corpPlayer"]:
                    corp_row["corpWin"] = 1
                    corp_row["corpScore"] = 3
                    corp_row["combinedScore"] = 3
                else:
                    corp_row["corpWin"] = 0
                    corp_row["corpScore"] = 0
                    corp_row["combinedScore"] = 0

            else:
                corp_row["eliminationGame"] = False
                corp_row["corpScore"] = int(table["corpScore"])
                corp_row["runnerScore"] = 0
                corp_row["combinedScore"] = int(table["corpScore"])
                corp_row["corpWin"] = 1 if int(table["corpScore"]) == 3 else 0
                corp_row["runnerWin"] = 0


            runner_row = {}
            runner_row["id"] = table["runnerPlayer"]
            runner_row["event"] = event_name
            runner_row["date"] = event_date
            runner_row["YM"] = event_date.to_period("M").strftime("%Y-%m")
            runner_row["table"] = table["tableNumber"]
            runner_row["round"] = rnd + 1
            runner_row["twoForOne"] = False
            runner_row["intentionalDraw"] = False # not reported
            runner_row["runnerPlay"] = 1
            runner_row["corpPlay"] = 0
            if table.get("eliminationGame"):
                runner_row["eliminationGame"] = True
                runner_row["corpScore"] = 0
                runner_row["corpWin"] = 0
                if table["winner_id"] == table["runnerPlayer"]:
                    runner_row["runnerWin"] = 1
                    runner_row["runnerScore"] = 3
                    runner_row["combinedScore"] = 3
                else:
                    runner_row["runnerWin"] = 0
                    runner_row["runnerScore"] = 0
                    runner_row["combinedScore"] = 0
            else:
                runner_row["eliminationGame"] = False
                runner_row["runnerScore"] = int(table["runnerScore"])
                runner_row["corpScore"] = 0
                runner_row["combinedScore"] = int(table["runnerScore"])
                runner_row["runnerWin"] = 1 if int(table["runnerScore"]) == 3 else 0
                runner_row["corpWin"] = 0

            corp_df = pd.DataFrame([corp_row])
            runner_df = pd.DataFrame([runner_row])
            records = pd.concat([records, corp_df, runner_df], ignore_index=True)

    augmented_records = pd.merge(
        records,
        players[["id", "name", "rank", "corpIdentity", "runnerIdentity", "corpFaction", "runnerFaction"]],
        on="id",
        how="left",
    )

    return augmented_records


def augment_player_records(matches, players):
    df = pd.merge(
        matches,
        players[["id", "name", "rank", "corpIdentity", "runnerIdentity", "corpFaction", "runnerFaction"]],
        on="id",
        how="left",
    )
    df["runnerWin"] = df.apply(lambda row: 1 if runner_won(row) else 0, axis=1)
    df["corpWin"] = df.apply(lambda row: 1 if corp_won(row) else 0, axis=1)
    df["runnerPlay"] = df.apply(
        lambda row: 1 if (not row["eliminationGame"] or row["role"] == "runner") else 0,
        axis=1,
    )
    df["corpPlay"] = df.apply(
        lambda row: 1 if (not row["eliminationGame"] or row["role"] == "corp") else 0,
        axis=1,
    )

    return df

def parse_filename(filepath):
    # Extract the basename of the file (remove directory path)
    dirname = os.path.dirname(filepath)
    basename = os.path.basename(filepath)

    # Remove the file extension (.json)
    filename_without_extension, _ = os.path.splitext(basename)

    # Define a regex pattern to match the desired parts of the filename
    pattern = r"(.+)-(.+)"

    match = re.match(pattern, filename_without_extension)
    if match:
        # Extract the matched parts
        part1 = match.group(1)  # The date and identifiers (e.g., "2023-11-19-amt-nov")
        part2 = match.group(2)  # The specific identifier (e.g., "cobra" or "aesops")
        return dirname, part1, part2
    else:
        # Handle filenames that do not match the pattern
        return None, None, None

def validate_file(filepath, id_df):
    dirname, prefix, source = parse_filename(filepath)
    tournaments=[[prefix, source]]
    flattened_matches, paired_matches = aggregate_tournament_data(id_df, tournaments)
    print(paired_matches.head(5))

def corp_won(row):
    if row["eliminationGame"]:
        return row["role"] == "corp" and row["winner"]
    return row["corpScore"] == 3


def runner_won(row):
    if row["eliminationGame"]:
        return row["role"] == "runner" and row["winner"]
    return row["runnerScore"] == 3


def get_runner_win_rate(df) -> pd.DataFrame:
    result = (
        df.groupby("runnerIdentity")
        .agg(
            total_wins=pd.NamedAgg(column="runnerWin", aggfunc="sum"),
            matches_played=pd.NamedAgg(column="runnerPlay", aggfunc="sum"),
        )
        .reset_index()
    )
    result["win_ratio"] = result["total_wins"] / result["matches_played"]
    result_sorted = result.sort_values(by="win_ratio", ascending=False).reset_index(
        drop=True
    )

    return result_sorted


def get_corp_win_rate(df) -> pd.DataFrame:
    result = (
        df.groupby("corpIdentity")
        .agg(
            total_wins=pd.NamedAgg(column="corpWin", aggfunc="sum"),
            matches_played=pd.NamedAgg(column="corpPlay", aggfunc="sum"),
        )
        .reset_index()
    )
    result["win_ratio"] = result["total_wins"].astype(float) / result["matches_played"].astype(float)
    result_sorted = result.sort_values(by="win_ratio", ascending=False).reset_index(
        drop=True
    )

    return result_sorted

def get_runner_win_rate_by_event_month(flattened) -> pd.DataFrame:
    runner_win_by_event_month = (
        flattened
        .groupby(
            [
                "event",
                "YM",
                "id",
                "name",
                "runnerIdentity",
                "runnerFaction",
            ]
        )
        .agg(
            total_wins=pd.NamedAgg(column="runnerWin", aggfunc="sum"),
            matches_played=pd.NamedAgg(column="runnerPlay", aggfunc="sum"),
        )
        .reset_index()
    )

    runner_win_by_event_month["win_ratio"] = runner_win_by_event_month["total_wins"].astype(
        float
    ) / runner_win_by_event_month["matches_played"].astype(float)

    return runner_win_by_event_month

def get_corp_win_rate_by_event_month(flattened) -> pd.DataFrame:
    corp_win_by_event_month = (
        flattened
        .groupby(
            [
                "event",
                "YM",
                "id",
                "name",
                "corpIdentity",
                "corpFaction",
            ]
        )
        .agg(
            total_wins=pd.NamedAgg(column="corpWin", aggfunc="sum"),
            matches_played=pd.NamedAgg(column="corpPlay", aggfunc="sum"),
        )
        .reset_index()
    )

    corp_win_by_event_month["win_ratio"] = corp_win_by_event_month["total_wins"].astype(
        float
    ) / corp_win_by_event_month["matches_played"].astype(float)

    return corp_win_by_event_month


def get_paired_match_records(flattened_event_records) -> pd.DataFrame:
    paired = pd.merge(
        flattened_event_records,
        flattened_event_records,
        on=["round", "table"],
        suffixes=("_left", "_right"),
    )
    paired = paired[paired["id_left"] < paired["id_right"]]
    match_dict = []
    didBreak = False
    for index, match_pair in paired.iterrows():
        try:
            if match_pair["corpPlay_left"]:
                match_dict.append(
                    {
                        "event": match_pair["event_left"],
                        "date": match_pair["date_left"],
                        "YM": match_pair["YM_left"],
                        "round": match_pair["round"],
                        "table": match_pair["table"],
                        "corp": match_pair["corpIdentity_left"],
                        "runner": match_pair["runnerIdentity_right"],
                        "corp_wins": match_pair["corpWin_left"],
                        "runner_wins": match_pair["runnerWin_right"],
                        "corp_player": match_pair["name_left"],
                        "corp_rank": match_pair["rank_left"],
                        "runner_player": match_pair["name_right"],
                        "runner_rank": match_pair["rank_right"],
                    }
                )
        except:
            print(match_pair)
            logging.exception("failed to create pairs for corp_played_left")
            break
        try:
            if match_pair["runnerPlay_left"]:
                match_dict.append(
                    {
                        "event": match_pair["event_left"],
                        "date": match_pair["date_left"],
                        "YM": match_pair["YM_left"],
                        "round": match_pair["round"],
                        "table": match_pair["table"],
                        "corp": match_pair["corpIdentity_right"],
                        "runner": match_pair["runnerIdentity_left"],
                        "corp_wins": match_pair["corpWin_right"],
                        "runner_wins": match_pair["runnerWin_left"],
                        "corp_player": match_pair["name_right"],
                        "corp_rank": match_pair["rank_right"],
                        "runner_player": match_pair["name_left"],
                        "runner_rank": match_pair["rank_left"],
                    }
                )
        except:
            print(match_pair)
            logging.exception("failed to create pairs for runner_played_left")
            break

    return pd.DataFrame(match_dict).reset_index(drop=True)


def get_grouped_player_results(player_records) -> pd.DataFrame:
    df = (
        player_records.groupby(["name", "corpIdentity", "runnerIdentity"])
        .agg(
            rank=pd.NamedAgg(column="rank", aggfunc="mean"),
            corp_wins=pd.NamedAgg(column="corpWin", aggfunc="sum"),
            corp_played=pd.NamedAgg(column="corpPlay", aggfunc="sum"),
            runner_wins=pd.NamedAgg(column="runnerWin", aggfunc="sum"),
            runner_played=pd.NamedAgg(column="runnerPlay", aggfunc="sum"),
        )
        .sort_values(by="rank", ascending=True)
        .reset_index()
    )
    df["corp_win_ratio"] = df["corp_wins"] / df["corp_played"]
    df["runner_win_ratio"] = df["runner_wins"] / df["runner_played"]
    return df


def get_paired_winrate(paired_results) -> pd.DataFrame:
    result = (
        paired_results.groupby(["corp", "runner"])
        .agg(
            corp_wins=pd.NamedAgg(column="corp_wins", aggfunc="sum"),
            games_played=pd.NamedAgg(column="corp_wins", aggfunc="count"),
        )
        .reset_index()
    )
    result["corp_win_ratio"] = result["corp_wins"] / result["games_played"]
    return result


def get_player_corp_matches(player_records, *players) -> pd.DataFrame:
    pairings = get_paired_results(player_records)
    res = pd.DataFrame(columns=pairings.columns)
    for player in players:
        found = pairings[pairings["corp_player"] == player]
        res = pd.concat([res, found], ignore_index=True)
    return res


def get_player_runner_matches(player_records, *players) -> pd.DataFrame:
    pairings = get_paired_results(player_records)
    res = pd.DataFrame(columns=pairings.columns)
    for player in players:
        found = pairings[pairings["runner_player"] == player]
        res = pd.concat([res, found], ignore_index=True)
    return res


def get_player_matches(player_records, *players) -> pd.DataFrame:
    res = pd.DataFrame(
        columns=get_player_corp_matches(player_records, players[0]).columns
    )
    for player in players:
        as_corp = get_player_corp_matches(player_records, player)
        as_runner = get_player_runner_matches(player_records, player)
        res = pd.concat([res, as_corp, as_runner], ignore_index=True).reset_index(
            drop=True
        )
    return res

def get_heatmap(event, paired_winrate, min_games=0):
    paired_subset = paired_winrate[paired_winrate["games_played"] > min_games]
    data = paired_subset.pivot(index="corp", columns="runner", values="corp_win_ratio")
    mask = data.isna()
    annot = paired_subset.pivot(index="corp", columns="runner", values="games_played")
    g = sns.heatmap(
        data=data,
        mask=mask,
        annot=annot,
        fmt=".0f",
        cmap="vlag_r",
        vmin=0.0,
        vmax=1.0,
    )
    min_plus1 = min_games+1
    plt.title(f'{event} - {min_plus1}+ obs - Corp Win Rates (Number is Total Games Played)', fontsize=12, pad=24, y=1)
    plt.suptitle("Blue for corp; red for runner", fontsize=9, y=.93)

    return g

def get_corp_popularity_by_month(flattened_matches):
    corp_popularity_by_month = (
        flattened_matches.groupby(
            [
                "YM",
                "corpIdentity",
                "corpFaction",
            ],
            as_index=False,
        )
        .size()
        .reset_index()
    )
    corp_total_ids_by_month = (
        corp_popularity_by_month.groupby(
            [
                "YM",
            ]
        )
        .agg(
            total_by_month=pd.NamedAgg(column="size", aggfunc="sum"),
        )
        .reset_index()
    )
    corp_total_ids_by_month.set_index("YM", inplace=True)
    corp_popularity_by_month_pct = pd.merge(
        corp_popularity_by_month, corp_total_ids_by_month, how="left", on="YM"
    )
    corp_popularity_by_month_pct["pct"] = (
        corp_popularity_by_month_pct["size"]
        / corp_popularity_by_month_pct["total_by_month"]
    )
    return corp_popularity_by_month_pct

def plot_corp_popularity_two_up(df, title, left_faction, right_faction, ymax=0.3):
    fig, axs = plt.subplots(1, 2, figsize=(10, 6))
    sns.lineplot(
        data=df[
            df["corpFaction"] == left_faction
        ],
        x="YM",
        y="pct",
        hue="corpIdentity",
        ax=axs[0],
    )
    sns.lineplot(
        data=df[
            df["corpFaction"] == right_faction
        ],
        x="YM",
        y="pct",
        hue="corpIdentity",
        ax=axs[1],
    )
    axs[0].legend(loc="upper left", bbox_to_anchor=(0, -0.25))
    axs[1].legend(loc="upper left", bbox_to_anchor=(0, -0.25))
    axs[0].set_ylim(0, ymax)
    axs[1].set_ylim(0, ymax)
    fig.suptitle(title, fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 1])  # Adjust the layout to make room for the suptitle

def get_runner_popularity_by_month(flattened_matches):
    runner_popularity_by_month = (
        flattened_matches.groupby(
            [
                "YM",
                "runnerIdentity",
                "runnerFaction",
            ],
            as_index=False,
        )
        .size()
        .reset_index()
    )
    runner_total_ids_by_month = (
        runner_popularity_by_month.groupby(
            [
                "YM",
            ]
        )
        .agg(
            total_by_month=pd.NamedAgg(column="size", aggfunc="sum"),
        )
        .reset_index()
    )
    runner_total_ids_by_month.set_index("YM", inplace=True)
    runner_popularity_by_month_pct = pd.merge(
        runner_popularity_by_month, runner_total_ids_by_month, how="left", on="YM"
    )
    runner_popularity_by_month_pct["pct"] = (
        runner_popularity_by_month_pct["size"]
        / runner_popularity_by_month_pct["total_by_month"]
    )
    return runner_popularity_by_month_pct

def plot_runner_popularity_two_up(df, title, left_faction, right_faction, ymax=0.4):
    fig, axs = plt.subplots(1, 2, figsize=(10, 6))
    sns.lineplot(
        data=df[
            df["runnerFaction"] == left_faction
        ],
        x="YM",
        y="pct",
        hue="runnerIdentity",
        ax=axs[0],
    )
    axs[0].legend(loc="upper left", bbox_to_anchor=(0, -0.25))
    axs[0].set_ylim(0, ymax)
    if right_faction != "":
        sns.lineplot(
            data=df[
                df["runnerFaction"] == right_faction
            ],
            x="YM",
            y="pct",
            hue="runnerIdentity",
            ax=axs[1],
        )
        axs[1].set_ylim(0, ymax)
        axs[1].legend(loc="upper left", bbox_to_anchor=(0, -0.25))
    fig.suptitle(title, fontsize=14)
    plt.tight_layout()  # Adjust the layout to make room for the suptitle

def plot_runner_popularity_one_up(df, title, left_faction, ymax=0.3):
    fig, axs = plt.subplots(1, 1, figsize=(10, 6))
    sns.lineplot(
        data=df[
            df["runnerFaction"] == left_faction
        ],
        x="YM",
        y="pct",
        hue="runnerIdentity",
        ax=axs,
    )
    axs.legend(loc="upper left", bbox_to_anchor=(0, -0.25))
    axs.set_ylim(0, ymax)
    fig.suptitle(title, fontsize=16)
    plt.tight_layout()  # Adjust the layout to make room for the suptitle

def plot_corp_win_rate_over_time(corp_win_rate_by_event_month, title, faction):
    ordered_months = sorted(corp_win_rate_by_event_month["YM"].unique())

    ordered_ids = sorted(
        corp_win_rate_by_event_month[corp_win_rate_by_event_month["corpFaction"] == faction][
            "corpIdentity"
        ].unique()
    )

    g = sns.FacetGrid(
        corp_win_rate_by_event_month[corp_win_rate_by_event_month["corpFaction"] == faction],
        col="corpIdentity",
        col_order=ordered_ids,
        col_wrap=3,
        height=4,
        aspect=1.5,
    )
    g.map(
        sns.stripplot,
        "YM",
        "win_ratio",
        order=ordered_months,
        jitter=0.3,
        marker="o",
        size=15,
        edgecolor="royalblue",
        color="none",
        linewidth=1,
    )
    g.set_titles("{col_name}")  # Set each subplot title to the corpFaction value
    g.figure.suptitle(f"{title}: {faction}", fontsize=14)
    g.figure.subplots_adjust(top=.9)
    g.set_axis_labels("Date", "Win Ratio")  # Set common X and Y axis labels

def plot_runner_win_rate_over_time(runner_win_rate_by_event_month, title, faction):
    ordered_months = sorted(runner_win_rate_by_event_month["YM"].unique())

    ordered_ids = sorted(
        runner_win_rate_by_event_month[runner_win_rate_by_event_month["runnerFaction"] == faction][
            "runnerIdentity"
        ].unique()
    )

    g = sns.FacetGrid(
        runner_win_rate_by_event_month[runner_win_rate_by_event_month["runnerFaction"] == faction],
        col="runnerIdentity",
        col_order=ordered_ids,
        col_wrap=3,
        height=4,
        aspect=1.5,
    )
    g.map(
        sns.stripplot,
        "YM",
        "win_ratio",
        order=ordered_months,
        jitter=0.3,
        marker="o",
        size=15,
        edgecolor="royalblue",
        color="none",
        linewidth=1,
    )
    g.set_titles("{col_name}")  # Set each subplot title to the runnerFaction value
    g.figure.suptitle(f"{title}: {faction}", fontsize=14)
    g.figure.subplots_adjust(top=.9)
    g.set_axis_labels("Date", "Win Ratio")  # Set common X and Y axis labels
