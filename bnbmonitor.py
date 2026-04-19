import sys
import argparse
import time
import os
from src.config import load_config
from src.scraper import get_results
from src.processor import db_results_to_df, style_df, db_results_to_monitor_df, is_search_result_identical
from src.exporter import export_to_file, html_make_clickable, export_monitor_report
from src.database import reset_db, save_search_results, list_searches, get_results_by_search_id, get_all_results_with_metadata, get_last_search
from src.notifier import check_and_notify

def run_search_and_save(config):
    params = config["search_parameters"]
    print(f"""Search Parameters:
Check-In Date: {params['checkin']}
Check-Out Date: {params['checkout']}
Adult Count: {params['adult_count']}
Price Range: ${params['price_min']} - ${params['price_max']}
Search Box (bounding box): {params['search_box']}
    """)

    print("Fetching results from Airbnb...")
    try:
        results = get_results(config)
    except Exception as e:
        print(f"Error fetching results: {e}")
        return False
    
    if not results:
        print("No results found for the given parameters.")
        return False

    # Check if results are different from the last search
    last_search = get_last_search(config)
    if last_search:
        old_results = get_results_by_search_id(config, last_search['id'])
        if is_search_result_identical(results, old_results, params, last_search, config):
            print("Search results are identical to the previous search. Skipping database log.")
            # Still check for target price and notify even if not saving to DB
            check_and_notify(config, results)
            return True

    print(f"Found {len(results)} results. Saving to database...")
    save_search_results(config, results)
    print("Search completed and results saved to database.")

    # Check for target price and notify
    check_and_notify(config, results)

    return True

def main():
    parser = argparse.ArgumentParser(description="Airbnb Monitor")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("reset", help="Reset the database")
    subparsers.add_parser("run-search", help="Run search and save to DB")
    subparsers.add_parser("search-list", help="List searches from DB")
    
    report_parser = subparsers.add_parser("report", help="Generate HTML report")
    report_parser.add_argument("--sno", type=int, help="Search ID (SNO) to generate report for. If omitted, generates monitor report.")
    
    watch_parser = subparsers.add_parser("watch", help="Continuously run search and save to DB")
    watch_parser.add_argument("--period", type=int, required=True, help="Period in minutes between searches")
    watch_parser.add_argument("--daemon", action="store_true", help="Run in background as a daemon")
    
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
            if args.sno:
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
            else:
                print("Generating monitor report over time...")
                results_with_metadata = get_all_results_with_metadata(config)
                if not results_with_metadata:
                    print("No data available in database to generate monitor report.")
                    return
                
                stats_df = db_results_to_monitor_df(results_with_metadata)
                output_file = "monitor_report"
                print(f"Exporting monitor report to {output_file}.html...")
                export_monitor_report(stats_df, output_file)
            
            print("Done!")
            return

        if args.command == "run-search":
            run_search_and_save(config)
            return

        if args.command == "watch":
            if args.daemon:
                print(f"Starting watch mode in background. Logging to bnbmonitor_watch.log")
                try:
                    pid = os.fork()
                    if pid > 0:
                        sys.exit(0)
                except OSError as e:
                    print(f"Fork failed: {e}")
                    sys.exit(1)
                
                os.setsid()
                try:
                    pid = os.fork()
                    if pid > 0:
                        sys.exit(0)
                except OSError as e:
                    print(f"Second fork failed: {e}")
                    sys.exit(1)

                # Redirect standard file descriptors
                sys.stdout = open('bnbmonitor_watch.log', 'a', buffering=1)
                sys.stderr = open('bnbmonitor_watch.log', 'a', buffering=1)
                print(f"\n--- Watch mode daemon started at {time.ctime()} ---")

            print(f"Watch mode active. Period: {args.period} minutes.")
            run_search_and_save(config)
            try:
                while True:
                    print(f"Sleeping for {args.period} minutes...")
                    time.sleep(args.period * 60)
                    run_search_and_save(config)
            except KeyboardInterrupt:
                print("\nWatch mode stopped.")
            except Exception as e:
                print(f"Daemon encountered an error: {e}")
            return

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
