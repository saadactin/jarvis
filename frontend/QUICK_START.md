# Quick Start Guide

## Getting Started

1. **Start the Backend**:
   ```bash
   cd jarvis-main
   python app.py
   ```
   Backend runs on `http://localhost:5009`

2. **Start Universal Migration Service** (optional, for direct migrations):
   ```bash
   cd universal_migration_service
   python app.py
   ```
   Service runs on `http://localhost:5010`

3. **Open Frontend**:
   - Simply open `index.html` in your browser
   - Or use a local server:
     ```bash
     # Python
     python -m http.server 8080
     
     # Node.js
     npx http-server -p 8080
     ```
   - Navigate to `http://localhost:8080`

## First Time Setup

1. **Register Account**:
   - Click "Sign up" on login page
   - Fill in username, email, password
   - Click "Create Account"

2. **Login**:
   - Use your credentials to login
   - You'll be redirected to dashboard

3. **✅ Universal Migration Service (Automatic!)**:
   - No manual registration needed!
   - The service is automatically registered and started when the backend starts
   - You can go directly to creating operations

4. **Create Your First Operation**:
   - Go to "Operations" page
   - Click "Create Operation"
   - Follow the 6-step wizard:
     1. Select source (PostgreSQL, MySQL, Zoho, SQL Server)
     2. Select destination (ClickHouse, PostgreSQL, MySQL)
     3. Enter source connection details
     4. Enter destination connection details
     5. Set schedule and operation type
     6. Review and submit

## Common Tasks

### View Operations
- Go to "Operations" page
- Use filters to find specific operations
- Click "View" to see details

### Execute Operation Immediately
- Go to operation details page
- Click "Execute Now" button
- Operation will start immediately

### Check Operation Status
- Operations page shows current status
- Operation details page shows detailed status
- Running operations update automatically

### Manage Database Masters
- Go to "Database Masters" page
- Add, edit, or delete services
- Each service represents a microservice endpoint

## Troubleshooting

### Can't Login
- Check backend is running
- Verify credentials
- Check browser console for errors

### Operations Not Executing
- Verify Universal Migration Service is registered
- Check service URL is correct
- Ensure backend scheduler is running

### API Errors
- Check backend is running on port 5009
- Verify CORS is enabled in backend
- Check browser console for detailed errors

### Page Not Loading
- Check all JavaScript files are loaded
- Open browser console (F12) for errors
- Verify file paths are correct

## Browser Compatibility

- Chrome (recommended)
- Firefox
- Edge
- Safari

## Support

For issues:
1. Check browser console (F12) for errors
2. Verify backend is running
3. Check API configuration in `js/config.js`
4. Review README.md for detailed documentation

