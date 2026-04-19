import pandas as pd
import json

def is_search_result_identical(new_results, old_db_results, new_params, old_db_search_row, config):
    # 1. Compare parameters
    params_match = (
        old_db_search_row["checkin"] == new_params["checkin"] and
        old_db_search_row["checkout"] == new_params["checkout"] and
        old_db_search_row["adult_count"] == new_params["adult_count"] and
        old_db_search_row["price_min"] == new_params["price_min"] and
        old_db_search_row["price_max"] == new_params["price_max"] and
        old_db_search_row["search_box"] == json.dumps(new_params["search_box"])
    )
    
    if not params_match:
        return False

    # 2. Compare results
    if len(new_results) != len(old_db_results):
        return False

    # Format new results to match DB format for easy comparison
    bnb_url = config["bnb_url"]
    get_total_fn = lambda x: x["price"]["break_down"][-1]["amount"]
    
    formatted_new = []
    for item in new_results:
        rating = item.get("rating", {}).get("value")
        bed_count = ""
        primary_line = item.get("structuredContent", {}).get("primaryLine", [])
        if primary_line:
            bed_count = primary_line[-1].get("body", "")
        
        name = item.get("name")
        room_url = f"{bnb_url}rooms/{item.get('room_id')}"
        total_price = get_total_fn(item)
        
        formatted_new.append({
            "name": name,
            "rating": rating,
            "bed_count": bed_count,
            "room_url": room_url,
            "total_price": float(total_price)
        })

    # Convert old_db_results to list of dicts if they are sqlite3.Row
    formatted_old = []
    for row in old_db_results:
        formatted_old.append({
            "name": row["name"],
            "rating": row["rating"],
            "bed_count": row["bed_count"],
            "room_url": row["room_url"],
            "total_price": float(row["total_price"])
        })

    # Sort both to ensure order-independent comparison
    sort_key = lambda x: (x["room_url"], x["total_price"])
    formatted_new.sort(key=sort_key)
    formatted_old.sort(key=sort_key)

    return formatted_new == formatted_old

def db_results_to_df(db_rows):
    headers = ["Name", "Rating", "Bed Count", "URL", "Total Price"]
    data = []
    for row in db_rows:
        data.append([
            row["name"],
            row["rating"],
            row["bed_count"],
            row["room_url"],
            row["total_price"]
        ])
    
    df = pd.DataFrame(data, columns=headers)
    # Sort by price since DB might not be sorted
    df = df.sort_values(by="Total Price").reset_index(drop=True)
    return df

def db_results_to_monitor_df(results_with_metadata):
    if not results_with_metadata:
        return pd.DataFrame()
    
    # Convert sqlite3.Row objects to list of dicts for pandas
    data = [dict(row) for row in results_with_metadata]
    df = pd.DataFrame(data)
    
    # Ensure total_price is numeric
    df['total_price'] = pd.to_numeric(df['total_price'])
    
    # Group by search_id and timestamp to calculate stats
    stats = df.groupby(['search_id', 'timestamp']).agg(
        mean_price=('total_price', 'mean'),
        median_price=('total_price', 'median'),
        result_count=('total_price', 'count')
    ).reset_index()
    
    # Sort by timestamp
    stats = stats.sort_values(by='timestamp')
    
    return stats

def style_df(df, currency, html_make_clickable_fn):
    # Make name column clickable and remove URL column
    df_copy = df.copy()
    df_copy["Name"] = df_copy[["Name", "URL"]].apply(html_make_clickable_fn, axis=1)
    # Format Total Price
    df_copy["Total Price"] = df_copy['Total Price'].apply(lambda x: f'${x:.2f}')
    df_copy.rename(columns={'Total Price': f'Total Price ({currency})'}, inplace=True)
    new_df = df_copy.drop(columns=["URL"])

    return new_df
