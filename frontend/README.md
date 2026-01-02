# Jarvis Migration System - Frontend

Complete frontend application for the Jarvis Migration System built with vanilla HTML, CSS, and JavaScript.

## Features

- **User Authentication**: Login and registration with JWT token management
- **Dashboard**: Overview with statistics and recent operations
- **Operations Management**: Create, view, execute, and manage migration operations
- **Database Masters**: Manage microservice registrations
- **Real-time Updates**: Automatic status polling for running operations
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Project Structure

```
frontend/
├── index.html              # Entry point (redirects)
├── login.html              # Login page
├── register.html           # Registration page
├── dashboard.html          # Dashboard/Home
├── operations.html         # Operations list
├── operation-detail.html   # Operation details
├── create-operation.html  # Create operation wizard
├── databases.html         # Database masters management
├── css/
│   ├── main.css           # Base styles
│   ├── layout.css         # Layout components
│   ├── components.css     # UI components
│   └── utilities.css      # Utility classes
├── js/
│   ├── config.js         # Configuration
│   ├── utils.js          # Utility functions
│   ├── auth.js           # Authentication
│   ├── api.js            # API client
│   ├── app.js            # Main app logic
│   ├── components/       # Reusable components
│   └── pages/           # Page-specific logic
└── assets/              # Images and icons
```

## Setup

### Prerequisites

- Modern web browser (Chrome, Firefox, Edge, Safari)
- Backend API running on `http://localhost:5009`

### Installation

1. **No build step required!** This is a vanilla JavaScript application.

2. **Configure API URL** (if needed):
   - Edit `js/config.js`
   - Update `BASE_URL` if your backend runs on a different port

3. **Open in browser**:
   - Simply open `index.html` in your browser
   - Or use a local web server:
     ```bash
     # Python 3
     python -m http.server 8080
     
     # Node.js (if you have http-server installed)
     npx http-server -p 8080
     ```

4. **Access the application**:
   - Open `http://localhost:8080` in your browser

## Usage

### First Time Setup

1. **Register a new account**:
   - Go to Register page
   - Fill in username, email, and password
   - Click "Create Account"

2. **Login**:
   - Use your credentials to login
   - You'll be redirected to the dashboard

3. **✅ Universal Migration Service (Automatic!)**:
   - No manual registration needed!
   - The service is automatically registered and started when the backend starts
   - You can go directly to creating operations

4. **Create your first operation**:
   - Go to "Operations" page
   - Click "Create Operation"
   - Follow the wizard steps:
     1. Select source (PostgreSQL, MySQL, Zoho, SQL Server)
     2. Select destination (ClickHouse, PostgreSQL, MySQL)
     3. Configure source connection
     4. Configure destination connection
     5. Set schedule and operation type
     6. Review and submit

### Creating Operations

The create operation wizard guides you through:

1. **Source Selection**: Choose your source database type
2. **Destination Selection**: Choose your destination database type
3. **Source Configuration**: Enter connection details for source
4. **Destination Configuration**: Enter connection details for destination
5. **Schedule**: Set when the migration should run
6. **Review**: Review all settings before submitting

### Viewing Operations

- **Operations List**: See all your operations with filters
- **Operation Details**: Click on any operation to see:
  - Current status
  - Migration results
  - Configuration details
  - Timeline (created, started, completed)

### Executing Operations

- Operations scheduled for the future will run automatically
- You can manually execute operations by clicking "Execute" button
- Running operations will show real-time status updates

## API Integration

The frontend communicates with the backend API at `http://localhost:5009`.

### Endpoints Used

- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user
- `GET /api/database-master` - List database masters
- `POST /api/database-master` - Create database master
- `PUT /api/database-master/:id` - Update database master
- `DELETE /api/database-master/:id` - Delete database master
- `GET /api/operations` - List operations
- `GET /api/operations/:id` - Get operation details
- `GET /api/operations/:id/status` - Get operation status
- `GET /api/operations/summary` - Get operations summary
- `POST /api/operations` - Create operation
- `PUT /api/operations/:id` - Update operation
- `DELETE /api/operations/:id` - Delete operation
- `POST /api/operations/:id/execute` - Execute operation

## Features

### Authentication

- JWT token stored in localStorage
- Automatic token refresh
- Protected routes
- Auto-logout on token expiry

### Real-time Updates

- Status polling for running operations (every 5 seconds)
- Automatic dashboard refresh (every 10 seconds)
- Live status updates without page refresh

### Form Validation

- Client-side validation before API calls
- Clear error messages
- Required field indicators
- Email format validation
- Password strength requirements

### Error Handling

- User-friendly error messages
- Toast notifications for actions
- Network error handling
- API error handling

### Responsive Design

- Mobile-first approach
- Works on all screen sizes
- Collapsible sidebar on mobile
- Touch-friendly buttons

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Edge (latest)
- Safari (latest)

## Development

### File Organization

- **HTML**: Page structure and layout
- **CSS**: Organized by purpose (main, layout, components, utilities)
- **JavaScript**: Modular structure with separate files for each page/component

### Adding New Features

1. Create HTML page in root directory
2. Create corresponding JavaScript in `js/pages/`
3. Add route in sidebar (`js/components/sidebar.js`)
4. Update navigation as needed

### Styling

- Uses CSS custom properties (variables) for theming
- Component-based CSS organization
- Utility classes for common patterns
- Responsive breakpoints at 768px

## Troubleshooting

### CORS Errors

If you see CORS errors, make sure:
- Backend has CORS enabled
- API URL in `config.js` matches your backend URL

### Authentication Issues

- Clear localStorage and login again
- Check if token is expired
- Verify backend is running

### API Connection Errors

- Verify backend is running on correct port
- Check API URL in `config.js`
- Check browser console for detailed errors

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Dark mode
- [ ] Operation templates
- [ ] Bulk operations
- [ ] Export functionality
- [ ] Advanced filtering
- [ ] Charts and analytics
- [ ] User settings page

## License

Part of the Jarvis Migration System project.

