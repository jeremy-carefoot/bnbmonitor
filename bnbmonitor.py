import sys
import argparse
from src.config import load_config
from src.scraper import get_results
from src.processor import db_results_to_df, style_df
from src.exporter import export_to_file, html_make_clickable
from src.database import reset_db, save_search_results, list_searches, get_results_by_search_id

def main():
    parser = argparse.ArgumentParser(description="Airbnb Monitor")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("reset", help="Reset the database")
    subparsers.add_parser("run-search", help="Run search and save to DB")
    subparsers.add_parser("search-list", help="List searches from DB")
    
    report_parser = subparsers.add_parser("report", help="Generate HTML report from a previous search")
    report_parser.add_argument("--sno", type=int, required=True, help="Search ID (SNO) to generate report for")
    
    # If no arguments, print help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
        
    args = parser.parse_args()
    
    try:
        config = load_config()
        
        if args.command == "reset":
            reset_db(config)
            return

        if args.command == "search-list":
            searches = list_searches(config)
            if not searches:
                print("No searches found in database.")
            else:
                print(f"{'ID':<4} | {'Timestamp':<20} | {'Check-in':<10} | {'Check-out':<10} | {'Adults':<6} | {'Price Range':<15}")
                print("-" * 80)
                for s in searches:
                    price_range = f"${s[5]} - ${s[6]}"
                    print(f"{s[0]:<4} | {s[1]:<20} | {s[2]:<10} | {s[3]:<10} | {s[4]:<6} | {price_range:<15}")
            return

        if args.command == "report":
            print(f"Generating report for search ID: {args.sno}")
            rows = get_results_by_search_id(config, args.sno)
            if not rows:
                print(f"No results found for search ID {args.sno}.")
                return
            
            dataframe = db_results_to_df(rows)
            styled_dataframe = style_df(
                dataframe, 
                config["currency"], 
                html_make_clickable
            )
            
            output_file = f"{config['output_file']}_{args.sno}"
            print(f"Exporting results to {output_file}.html...")
            export_to_file(
                dataframe, 
                output_file, 
                config, 
                styled_dataframe
            )
            print("Done!")
            return

        if args.command == "run-search":
            params = config["search_parameters"]
            print(f"""Search Parameters:
    Check-In Date: {params['checkin']}
    Check-Out Date: {params['checkout']}
    Adult Count: {params['adult_count']}
    Price Range: ${params['price_min']} - ${params['price_max']}
    Search Box (bounding box): {params['search_box']}
            """)

            print("Fetching results from Airbnb...")
            results = get_results(config)
            
            if not results:
                print("No results found for the given parameters.")
                return

            print(f"Found {len(results)} results. Saving to database...")
            save_search_results(config, results)
            print("Search completed and results saved to database.")
            return

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
