from datetime import datetime

def html_make_clickable(row) -> str:
    text = row['Name']
    url = row['URL']
    return f'<a href="{url}" target="_blank">{text}</a>'

def html_construct_list(params: dict) -> str:
    html_list_items = "".join(f"<li><b>{key}</b>: {val}</li>" for key, val in params.items())
    return f'<ul>{html_list_items}</ul>\n'

def export_to_file(df, filename: str, config: dict, styled_df):
    now = datetime.now()
    formatted_now = now.strftime("%B %d, %Y %H:%M")
    iso_filename_timestamp = now.strftime("%Y-%m-%d_%H%M%S")

    currency = config["currency"]
    params = config["search_parameters"]
    
    mean_total_price = df["Total Price"].mean()
    median_total_price = df["Total Price"].median()
    result_count = df.shape[0]

    search_params = {
        "Check-In Date": params["checkin"],
        "Check-Out Date": params["checkout"],
        "Guest Count": str(params["adult_count"]),
        "Price Range (approximate)": f"${params['price_min']} - ${params['price_max']}",
        "Area (geographical bounding box)": str(params["search_box"])
    }

    stats = {
        f"Median Total Price ({currency})": f"${median_total_price:.2f}",
        f"Mean Total Price ({currency})": f"${mean_total_price:.2f}"
    }

    html_search_param_list = html_construct_list(search_params)
    html_stat_list = html_construct_list(stats)

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
