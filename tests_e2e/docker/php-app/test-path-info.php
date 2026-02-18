<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PATH_INFO Test</title>
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
            border-bottom: 3px solid #2196F3;
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
        .info {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        pre {
            background: #f4f4f4;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }
        a {
            color: #2196F3;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PATH_INFO Test</h1>

        <?php if (isset($_SERVER['PATH_INFO']) && !empty($_SERVER['PATH_INFO'])): ?>
            <div class="success">
                <strong>Success!</strong> PATH_INFO is working correctly.
            </div>

            <h2>PATH_INFO Value</h2>
            <pre><?php echo htmlspecialchars($_SERVER['PATH_INFO']); ?></pre>

            <h2>Parsed Path Segments</h2>
            <pre><?php
                $segments = explode('/', trim($_SERVER['PATH_INFO'], '/'));
                print_r(array_filter($segments));
            ?></pre>

        <?php else: ?>
            <div class="info">
                <strong>Note:</strong> PATH_INFO is not set. Try accessing this page with additional path segments.
            </div>
        <?php endif; ?>

        <h2>Request Information</h2>
        <pre><?php
echo "SCRIPT_NAME:    " . ($_SERVER['SCRIPT_NAME'] ?? 'N/A') . "\n";
echo "REQUEST_URI:    " . ($_SERVER['REQUEST_URI'] ?? 'N/A') . "\n";
echo "PATH_INFO:      " . ($_SERVER['PATH_INFO'] ?? 'N/A') . "\n";
echo "QUERY_STRING:   " . ($_SERVER['QUERY_STRING'] ?? 'N/A') . "\n";
        ?></pre>

        <h2>Example Usage</h2>
        <p>PATH_INFO enables RESTful URL routing. Try these URLs:</p>
        <ul>
            <li><a href="/test-path-info.php/users">/test-path-info.php/users</a></li>
            <li><a href="/test-path-info.php/users/123">/test-path-info.php/users/123</a></li>
            <li><a href="/test-path-info.php/api/v1/products">/test-path-info.php/api/v1/products</a></li>
        </ul>

        <p><a href="/">← Back to Home</a></p>
    </div>
</body>
</html>
