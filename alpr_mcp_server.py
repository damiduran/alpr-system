import os
import sqlite3
from mcp.server import MCPServer

# Initialize the High-Level MCP Server
server = MCPServer("ALPR-System-MCP-Server")

# Resolve absolute path to the SQLite database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "alpr.db")

@server.tool(
    name="query_vehicle_rego",
    description="Search the ALPR database for sightings of a specific vehicle license plate / registration number."
)
def query_vehicle_rego(plate_number: str) -> str:
    """
    Query the ALPR SQLite database for recent detections of a given plate number.
    
    Args:
        plate_number: The license plate registration string to search for.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Look up last 5 sightings
        cursor.execute(
            "SELECT detection_date, detection_time, vehicle_make, vehicle_model, vehicle_color "
            "FROM detections WHERE plate_number LIKE ? ORDER BY id DESC LIMIT 5",
            (f"%{plate_number.strip()}%",)
        )
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return f"No records found for license plate '{plate_number}' in the ALPR system."
            
        summary = [f"Found {len(rows)} recent sighting(s) for '{plate_number}':"]
        for idx, row in enumerate(rows, 1):
            make = row['vehicle_make'] or 'Unknown Make'
            model = row['vehicle_model'] or 'Unknown Model'
            color = row['vehicle_color'] or 'Unknown Color'
            summary.append(
                f"{idx}. {row['detection_date']} at {row['detection_time']} - "
                f"{color} {make} {model}"
            )
        return "\n".join(summary)
    except Exception as e:
        return f"Error executing ALPR database query: {str(e)}"

@server.tool(
    name="list_recent_detections",
    description="Fetch a list of the most recently detected vehicles entering the property."
)
def list_recent_detections(limit: int = 5) -> str:
    """
    Retrieve the most recent license plate detections from the ALPR logs.
    
    Args:
        limit: The maximum number of recent detections to return. Defaults to 5.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT plate_number, detection_date, detection_time, vehicle_make, vehicle_model, vehicle_color "
            "FROM detections ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "No detections found in the ALPR database logs."
            
        summary = [f"Most recent {len(rows)} detections:"]
        for idx, row in enumerate(rows, 1):
            make = row['vehicle_make'] or 'Unknown Make'
            model = row['vehicle_model'] or 'Unknown Model'
            color = row['vehicle_color'] or 'Unknown Color'
            summary.append(
                f"{idx}. Plate: {row['plate_number']} | {row['detection_date']} at {row['detection_time']} - "
                f"{color} {make} {model}"
            )
        return "\n".join(summary)
    except Exception as e:
        return f"Error fetching recent ALPR detections: {str(e)}"

if __name__ == "__main__":
    print("[ALPR-MCP] Starting ALPR Model Context Protocol Server over SSE transport...")
    print(f"[ALPR-MCP] Targeting SQLite database at: {DB_PATH}")
    print("[ALPR-MCP] Running on http://127.0.0.1:8010")
    # Start the SSE server on localhost port 8010
    server.run(transport="sse", host="127.0.0.1", port=8010)
