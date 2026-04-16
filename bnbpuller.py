import pyairbnb
from datetime import datetime
import pandas as pd

BNB_URL = "https://www.airbnb.ca/"
OUTPUT_FILE = "results"

# SEARCH PARAMS
SEARCH_BOX=[-114.117651,51.036941,-114.065595,51.057203] # Search bbox can be found from http://www.bboxfinder.com
CHECKIN="2026-07-10"
CHECKOUT="2026-07-12"
ADULT_COUNT=3
PRICE_MIN=0
PRICE_MAX=2000

# Other params
CURRENCY="CAD"
LANGUAGE="en"

def export_to_file(df, filename: str):
    now = datetime.now()
    formatted_now = now.strftime("%B %d, %Y %H:%M")
    iso_filename_timestamp = now.strftime("%Y-%m-%d_%H%M%S")

    mean_total_price = df["Total Price"].mean()
    median_total_price = df["Total Price"].median()
    result_count = df.shape[0]

    search_params = {
        "Check-In Date": CHECKIN,
        "Check-Out Date": CHECKOUT,
        "Guest Count": str(ADULT_COUNT),
        "Price Range (approximate)": f"${PRICE_MIN} - ${PRICE_MAX}",
        "Area (geographical bounding box)": str(SEARCH_BOX)
    }

    stats = {
        f"Median Total Price ({CURRENCY})": f"${median_total_price:.2f}",
        f"Mean Total Price ({CURRENCY})": f"${mean_total_price:.2f}"
    }

    html_search_param_list = html_construct_list(search_params)
    html_stat_list = html_construct_list(stats)

    styled_df = style_df(df)
    html_table = styled_df.to_html(index=False, escape=False, justify="end")

    with open(f"{filename}-{iso_filename_timestamp}.html", 'w') as f:
        f.write("<html>\n<head><title>BnBPuller Results</title></head>\n<body>\n")
        f.write(f"<h1>Search Query Summary ({formatted_now})</h1>\n")
        f.write("<h2>Search Parameters:</h2>\n")
        f.write(html_search_param_list)
        f.write("<h2>Price Analysis:</h2>\n")
        f.write(f"<h3>{result_count} results</h3>\n")
        f.write(html_stat_list)
        f.write(html_table)
        f.write("\n</body>\n</html>")

def html_make_clickable(row) -> str:
    text = row['Name']
    url = row['URL']
    return f'<a href="{url}" target="_blank">{text}</a>'

def html_construct_list(params: dict) -> str:
    html_list_items = "".join(f"<li><b>{key}</b>: {val}</li>" for key, val in params.items())
    return f'<ul>{html_list_items}</ul>\n'

def get_results():
    results = pyairbnb.search_all(
        currency=CURRENCY,
        language=LANGUAGE,
        zoom_value=1,
        check_in=CHECKIN,
        check_out=CHECKOUT,
        adults=ADULT_COUNT,
        price_min=PRICE_MIN,
        price_max=PRICE_MAX,
        sw_long=SEARCH_BOX[0],
        sw_lat=SEARCH_BOX[1],
        ne_long=SEARCH_BOX[2],
        ne_lat=SEARCH_BOX[3],
    )
    return results

def style_df(df):
    # Make name column clickable and remove URL column
    df["Name"] = df[["Name", "URL"]].apply(html_make_clickable, axis=1)
    # Format Total Price
    df["Total Price"] = df['Total Price'].apply(lambda x: f'${x:.2f}')
    df.rename(columns={'Total Price': f'Total Price ({CURRENCY})'}, inplace=True)
    new_df = df.drop(columns=["URL"])

    return new_df

def results_to_sorted_df(results):
    headers = ["Name", "Rating", "Bed Count", "URL", "Total Price"]
    # Sort ascending by sort function (total price)
    get_total_fn = lambda x: x["price"]["break_down"][-1]["amount"]
    sorted_results = sorted(results, key=get_total_fn)

    data = []
    for item in sorted_results:
        data.append([
            item["name"], # name
            item["rating"]["value"], # rating
            item["structuredContent"]["primaryLine"][-1]["body"], # bed count
            f"{BNB_URL}rooms/{item["room_id"]}", # room URL
            get_total_fn(item) # price total
            ])

    df = pd.DataFrame(data, columns=headers)
    return df

def main():
    print(f"""Search Parameters:
    Check-In Date: {CHECKIN}
    Check-Out Date: {CHECKOUT}
    Adult Count: {ADULT_COUNT}
    Price Range: ${PRICE_MIN} - ${PRICE_MAX}
    Search Box (bounding box): {SEARCH_BOX}
    """)

    results = get_results()
    dataframe = results_to_sorted_df(results)
    export_to_file(dataframe, OUTPUT_FILE)

if __name__ == "__main__":
    main()