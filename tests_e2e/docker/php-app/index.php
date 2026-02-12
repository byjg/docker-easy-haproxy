<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHP-FPM with EasyHAProxy</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .info-table th,
        .info-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .info-table th {
            background: #f8f9fa;
            font-weight: bold;
            width: 200px;
        }
        .info-table tr:hover {
            background: #f8f9fa;
        }
        a {
            color: #4CAF50;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PHP-FPM with EasyHAProxy FastCGI Plugin</h1>

        <div class="success">
            <strong>Success!</strong> PHP is running via FastCGI protocol through HAProxy.
        </div>

        <h2>FastCGI Environment</h2>
        <table class="info-table">
            <tr>
                <th>PHP Version</th>
                <td><?php echo PHP_VERSION; ?></td>
            </tr>
            <tr>
                <th>Server Software</th>
                <td><?php echo $_SERVER['SERVER_SOFTWARE'] ?? 'N/A'; ?></td>
            </tr>
            <tr>
                <th>Document Root</th>
                <td><code><?php echo $_SERVER['DOCUMENT_ROOT'] ?? 'N/A'; ?></code></td>
            </tr>
            <tr>
                <th>Script Filename</th>
                <td><code><?php echo $_SERVER['SCRIPT_FILENAME'] ?? 'N/A'; ?></code></td>
            </tr>
            <tr>
                <th>Request URI</th>
                <td><code><?php echo $_SERVER['REQUEST_URI'] ?? 'N/A'; ?></code></td>
            </tr>
            <tr>
                <th>Request Method</th>
                <td><?php echo $_SERVER['REQUEST_METHOD'] ?? 'N/A'; ?></td>
            </tr>
            <tr>
                <th>Server Name</th>
                <td><?php echo $_SERVER['SERVER_NAME'] ?? 'N/A'; ?></td>
            </tr>
            <tr>
                <th>Server Port</th>
                <td><?php echo $_SERVER['SERVER_PORT'] ?? 'N/A'; ?></td>
            </tr>
            <tr>
                <th>HTTPS</th>
                <td><?php echo ($_SERVER['HTTPS'] ?? 'off') === 'on' ? 'Yes' : 'No'; ?></td>
            </tr>
            <tr>
                <th>PATH_INFO</th>
                <td><code><?php echo $_SERVER['PATH_INFO'] ?? 'Not set'; ?></code></td>
            </tr>
            <tr>
                <th>Gateway Interface</th>
                <td><?php echo $_SERVER['GATEWAY_INTERFACE'] ?? 'N/A'; ?></td>
            </tr>
        </table>

        <h2>Test Links</h2>
        <ul>
            <li><a href="/info.php">View PHP Info</a></li>
            <li><a href="/test-path-info.php/extra/path">Test PATH_INFO support</a></li>
        </ul>

        <h2>How This Works</h2>
        <p>
            This setup uses HAProxy with EasyHAProxy to proxy requests to PHP-FPM via the FastCGI protocol:
        </p>
        <ol>
            <li>HAProxy receives HTTP request on port 80</li>
            <li>The FastCGI plugin generates an <code>fcgi-app</code> configuration that defines CGI parameters (SCRIPT_FILENAME, DOCUMENT_ROOT, etc.)</li>
            <li>HAProxy uses this configuration to communicate with PHP-FPM via the FastCGI protocol</li>
            <li>HAProxy connects to PHP-FPM (via TCP port 9000 or Unix socket, depending on configuration)</li>
            <li>PHP-FPM processes the PHP script and returns the response</li>
            <li>HAProxy sends the response back to the client</li>
        </ol>

        <h2>Configuration</h2>
        <p>The FastCGI plugin is configured in <code>docker-compose-php-fpm.yml</code>:</p>
        <ul>
            <li><strong>document_root:</strong> <code>/var/www/html</code></li>
            <li><strong>index_file:</strong> <code>index.php</code></li>
            <li><strong>path_info:</strong> <code>true</code> (enables PATH_INFO support)</li>
        </ul>
    </div>
</body>
</html>
