import asyncio
import json
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse

os.environ["CONTEXTSLIM_EMBEDDING_PROVIDER"] = "openai"
os.environ["CONTEXTSLIM_DB_PATH"] = "/tmp/contextslim.db"

from contextslim import app as contextslim_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel")


class MCPClientTracker(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            if request.method == "POST" and request.url.path == "/mcp":
                body = await request.body()
                data = json.loads(body)
                if data.get("method") == "initialize":
                    params = data.get("params", {})
                    client_info = params.get("clientInfo", {})
                    name = client_info.get("name", "unknown")
                    version = client_info.get("version", "unknown")
                    protocol = params.get("protocolVersion", "unknown")
                    ip = request.client.host if request.client else "unknown"
                    logger.info("MCP client connected: %s v%s (protocol: %s, ip: %s)", name, version, protocol, ip)
                    contextslim_app.analytics.log_audit(
                        action="mcp_connect",
                        details={
                            "client_name": name,
                            "client_version": version,
                            "protocol_version": protocol,
                            "ip": ip,
                        },
                    )
        except Exception:
            pass
        return await call_next(request)


async def root(request: Request):
    return JSONResponse({
        "service": "ContextSlim Router",
        "status": "ok",
        "mcp_endpoint": "/mcp",
        "docs": "https://github.com/Deepak-ai-93/contextslim",
    })


async def admin_dashboard(request: Request):
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    try:
        with open(dashboard_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(html_content)
    except Exception as e:
        return HTMLResponse(f"<h3>Error loading dashboard: {str(e)}</h3>", status_code=500)


async def admin_stats(request: Request):
    admin_key = request.query_params.get("admin_key", "")
    if not contextslim_app.user_service.verify_admin(admin_key):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    conn = contextslim_app.analytics._get_conn()
    try:
        # Total users count
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        total_users = row[0] if row else 0
        
        # Total routing searches count
        row = conn.execute("SELECT COUNT(*) FROM analytics").fetchone()
        total_searches = row[0] if row else 0
        
        # Total tool executions count
        row = conn.execute("SELECT SUM(usage_count) FROM usage_stats").fetchone()
        total_tool_runs = row[0] if row and row[0] is not None else 0
        
        # Users list
        rows = conn.execute("SELECT id, email, name, role, created_at, last_active FROM users ORDER BY last_active DESC").fetchall()
        users_list = [dict(r) for r in rows]
        
        # Recent audit log entries
        rows = conn.execute("SELECT id, timestamp, user_email, action, details, success FROM audit_log ORDER BY timestamp DESC LIMIT 50").fetchall()
        audit_list = [dict(r) for r in rows]
        
        # Connected clients history (filtered from audit log where action is 'mcp_connect')
        rows = conn.execute("SELECT timestamp, details FROM audit_log WHERE action = 'mcp_connect' ORDER BY timestamp DESC LIMIT 30").fetchall()
        connected_clients = []
        for r in rows:
            details_str = r["details"]
            try:
                import ast
                details = ast.literal_eval(details_str)
            except Exception:
                details = {"client_name": details_str}
            connected_clients.append({
                "timestamp": r["timestamp"],
                "client_name": details.get("client_name", "unknown"),
                "client_version": details.get("client_version", "unknown"),
                "protocol_version": details.get("protocol_version", "unknown"),
                "ip": details.get("ip", "unknown"),
            })
        
        # Top used tools list
        rows = conn.execute("SELECT tool_id, usage_count, success_count, last_used FROM usage_stats ORDER BY usage_count DESC LIMIT 15").fetchall()
        top_tools = [dict(r) for r in rows]
        
        # Recent searches routing log
        rows = conn.execute("SELECT id, timestamp, query, tool_candidates, tools_returned, tool_selected, success FROM analytics ORDER BY timestamp DESC LIMIT 30").fetchall()
        recent_searches = [dict(r) for r in rows]
        
        return JSONResponse({
            "total_users": total_users,
            "total_searches": total_searches,
            "total_tool_runs": total_tool_runs,
            "users": users_list,
            "audit_log": audit_list,
            "connected_clients": connected_clients,
            "top_tools": top_tools,
            "recent_searches": recent_searches,
        })
    except Exception as e:
        logger.error("Error fetching admin stats: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        conn.close()


async def admin_user_report(request: Request):
    admin_key = request.query_params.get("admin_key", "")
    if not contextslim_app.user_service.verify_admin(admin_key):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    email = request.query_params.get("email", "")
    if not email:
        return JSONResponse({"error": "Missing email"}, status_code=400)
        
    try:
        usage = contextslim_app.analytics.get_user_usage(email)
        user = contextslim_app.user_service.get_user_by_email(email)
        if user:
            usage["name"] = user["name"]
            usage["role"] = user["role"]
            usage["created_at"] = user["created_at"]
        return JSONResponse(usage)
    except Exception as e:
        logger.error("Error fetching user report: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


app = contextslim_app.mcp.http_app(transport="streamable-http")
app.add_route("/", root)
app.add_route("/health", root)
app.add_route("/admindashboard", admin_dashboard)
app.add_route("/admindashbaord", admin_dashboard)
app.add_route("/api/admin/stats", admin_stats)
app.add_route("/api/admin/user-report", admin_user_report)
app.add_middleware(MCPClientTracker)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


async def _index_on_start():
    try:
        logger.info("Indexing tools on cold start...")
        await contextslim_app.indexing_service.index_all()
        logger.info("Indexing complete")
    except Exception as e:
        logger.error("Indexing failed: %s", e)


try:
    asyncio.run(_index_on_start())
except RuntimeError:
    pass
