/**
 * PM2 Ecosystem config for the EVM MCP HTTP server.
 * Deploy to VPS and run: pm2 start ecosystem.config.cjs
 *
 * The stdio server (server.js) is NOT managed by PM2 — it's launched on-demand by Cursor/Claude Desktop.
 */
module.exports = {
  apps: [
    {
      name: "evm-mcp-http",
      script: "dist/http-server.js",
      cwd: "/var/www/evm/mcp-server",
      interpreter: "node",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      env: {
        NODE_ENV: "production",
        MCP_HTTP_PORT: "3002",
      },
      // .env file is loaded by the server itself (dotenv)
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      error_file: "/var/log/evm/mcp-http-error.log",
      out_file: "/var/log/evm/mcp-http-out.log",
      merge_logs: true,
    },
  ],
};
