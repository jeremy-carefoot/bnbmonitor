import pandas as pd

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
