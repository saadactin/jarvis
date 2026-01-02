---
name: Frontend Development - Complete Implementation
overview: Create a complete frontend application for the Jarvis Migration System with all pages, components, styling, and API integration. The frontend will be built using vanilla HTML, CSS, and JavaScript (with modern ES6+) for simplicity and will include authentication, dashboard, operations management, and database master management.
todos: []
---

# Frontend Developm

ent - Complete Implementation Plan

## Project Structure

```javascript
frontend/
├── index.html                 # Main entry point
├── login.html                 # Login page
├── register.html              # Registration page
├── dashboard.html             # Dashboard/Home page
├── operations.html            # Operations list page
├── operation-detail.html       # Operation details page
├── create-operation.html      # Create operation wizard
├── databases.html             # Database masters management
├── css/
│   ├── main.css              # Main stylesheet
│   ├── components.css        # Component styles
│   ├── layout.css           # Layout styles
│   └── utilities.css        # Utility classes
├── js/
│   ├── config.js            # API configuration
│   ├── auth.js              # Authentication logic
│   ├── api.js               # API client functions
│   ├── utils.js             # Utility functions
│   ├── components/
│   │   ├── header.js        # Header component
│   │   ├── sidebar.js       # Sidebar navigation
│   │   ├── statusBadge.js   # Status badge component
│   │   ├── operationCard.js # Operation card component
│   │   ├── statsCard.js     # Stats card component
│   │   ├── dataTable.js     # Data table component
│   │   └── modal.js         # Modal component
│   ├── pages/
│   │   ├── login.js         # Login page logic
│   │   ├── register.js      # Register page logic
│   │   ├── dashboard.js     # Dashboard page logic
│   │   ├── operations.js    # Operations list logic
│   │   ├── operationDetail.js # Operation detail logic
│   │   ├── createOperation.js # Create operation wizard
│   │   └── databases.js     # Databases page logic
│   └── app.js               # Main application logic
├── assets/
│   ├── images/
│   └── icons/
└── README.md                 # Frontend documentation
```



## Implementation Tasks

### Phase 1: Project Setup and Base Structure

1. Create frontend folder structure
2. Create base HTML files (index.html, login.html, register.html, etc.)
3. Create CSS folder structure and base stylesheets
4. Create JavaScript folder structure and base files
5. Setup API configuration (config.js)
6. Create utility functions (utils.js)

### Phase 2: Core Infrastructure

1. Create API client (api.js) with all endpoints
2. Create authentication module (auth.js) with login/logout/token management
3. Create routing system (app.js) for navigation
4. Create common components (header, sidebar, modal, etc.)
5. Setup localStorage for token management

### Phase 3: Authentication Pages

1. Create login.html with form and validation
2. Create register.html with form and validation
3. Implement login.js with API integration
4. Implement register.js with API integration
5. Add authentication guards for protected pages

### Phase 4: Dashboard Page

1. Create dashboard.html with layout
2. Implement dashboard.js with stats fetching
3. Create stats cards component
4. Create recent operations section
5. Add real-time updates for running operations
6. Create charts for migration statistics

### Phase 5: Operations Management

1. Create operations.html with filters and table
2. Implement operations.js with CRUD operations
3. Create operation card component
4. Create operation detail page (operation-detail.html)
5. Implement operationDetail.js with status polling
6. Add execute, edit, delete functionality

### Phase 6: Create Operation Wizard

1. Create create-operation.html with multi-step wizard
2. Implement createOperation.js with step navigation
3. Create source selection step (PostgreSQL, MySQL, Zoho, SQL Server)
4. Create destination selection step (ClickHouse, PostgreSQL, MySQL)
5. Create connection configuration forms for each source/destination
6. Create schedule step with date/time picker
7. Create review step with validation
8. Implement form submission

### Phase 7: Database Masters Management

1. Create databases.html with list and forms
2. Implement databases.js with CRUD operations
3. Create add/edit database master modal
4. Add connection testing functionality
5. Create database master cards/list

### Phase 8: Styling and UI Polish

1. Create comprehensive CSS with modern design
2. Add responsive design for mobile/tablet
3. Add loading states and spinners
4. Add error handling and user feedback
5. Add animations and transitions
6. Create status badges with colors
7. Add tooltips and help text

### Phase 9: Advanced Features

1. Implement real-time status polling for running operations
2. Add operation summary endpoint integration
3. Add filters and search functionality
4. Add pagination for large lists
5. Add export functionality (future)
6. Add notifications/toasts for user actions

### Phase 10: Testing and Documentation

1. Test all pages and functionality
2. Test API integration
3. Test error handling
4. Create README.md with setup instructions
5. Add code comments
6. Test responsive design

## Detailed Page Specifications

### 1. index.html (Entry Point)

- Redirects to dashboard if authenticated
- Redirects to login if not authenticated
- Handles initial app load

### 2. login.html

- Email/Username input
- Password input
- Remember me checkbox
- Login button
- Link to register page
- Error message display
- Loading state

### 3. register.html

- Username input
- Email input
- Password input
- Confirm password input
- Register button
- Link to login page
- Validation messages

### 4. dashboard.html

- Header with user menu
- Sidebar navigation
- Stats cards (Total, Pending, Running, Completed, Failed)
- Recent operations table
- Quick actions section
- Migration success chart (optional)

### 5. operations.html

- Header with "Create Operation" button
- Filters (Status, Type, Date Range)
- Search input
- Operations table with columns:
- ID, Source, Destination, Status, Schedule, Created, Actions
- Pagination
- Bulk actions (future)

### 6. operation-detail.html

- Operation header with status badge
- Timeline (Created → Started → Completed)
- Configuration section (read-only)
- Migration results section:
- Tables migrated count
- Tables failed count
- Total records
- Detailed table list
- Error messages (if failed)
- Action buttons (Execute, Edit, Delete)

### 7. create-operation.html

- Multi-step wizard with progress indicator
- Step 1: Source Selection
- Radio buttons or cards for: PostgreSQL, MySQL, Zoho, SQL Server
- Step 2: Destination Selection
- Radio buttons or cards for: ClickHouse, PostgreSQL, MySQL
- Step 3: Source Configuration
- Dynamic form based on source type
- Connection fields (host, port, database, username, password)
- Test connection button
- Step 4: Destination Configuration
- Dynamic form based on destination type
- Connection fields
- Test connection button
- Step 5: Schedule & Type
- Operation type (Full/Incremental)
- Date picker
- Time picker
- Timezone selector
- Step 6: Review
- Summary of all selections
- Edit buttons for each step
- Submit button
- Navigation: Previous/Next buttons
- Step validation

### 8. databases.html

- Header with "Add Database" button
- Database masters list/cards
- Each card shows:
- Name
- Service URL
- Health status
- Actions (Edit, Delete, Test)
- Add/Edit modal form
- Connection test results

## CSS Design System

### Color Palette

- Primary: #1976d2 (Blue)
- Success: #2e7d32 (Green)
- Warning: #ed6c02 (Orange)
- Error: #d32f2f (Red)
- Info: #0288d1 (Light Blue)
- Background: #f5f5f5
- Surface: #ffffff
- Text Primary: #212121
- Text Secondary: #757575

### Typography

- Font Family: 'Roboto', 'Segoe UI', Arial, sans-serif
- Headings: 24px, 20px, 18px, 16px
- Body: 14px
- Small: 12px

### Spacing

- Base unit: 8px
- Common: 8px, 16px, 24px, 32px, 48px

### Components

- Cards: Shadow, rounded corners, padding
- Buttons: Primary, Secondary, Danger variants
- Forms: Input fields with labels, validation states
- Tables: Striped rows, hover effects
- Modals: Overlay, centered, close button
- Badges: Status indicators with colors

## JavaScript Architecture

### API Client (api.js)

- Base URL configuration
- Request/Response interceptors
- Token management
- Error handling
- Methods for all endpoints:
- Auth: login, register, getCurrentUser
- Database Masters: getAll, getById, create, update, delete
- Operations: getAll, getById, getStatus, getSummary, create, update, delete, execute

### Authentication (auth.js)

- Token storage/retrieval
- Login function
- Logout function
- Check authentication
- Get current user
- Token expiration handling

### Utilities (utils.js)

- Date formatting
- Status color mapping
- Form validation
- Error message formatting
- Loading state management
- Toast notifications

### Components

- Reusable UI components
- Event handling
- DOM manipulation helpers

## Features to Implement

1. **Authentication**

- Login/Register with validation
- JWT token management
- Protected routes
- Auto-logout on token expiry

2. **Dashboard**

- Real-time statistics
- Recent operations
- Quick actions
- Visual charts

3. **Operations**

- List with filters
- Create wizard
- Detail view
- Execute functionality
- Status polling

4. **Database Masters**

- CRUD operations
- Connection testing
- Service health

5. **UI/UX**

- Responsive design
- Loading states
- Error handling
- Success notifications
- Form validation

## Technical Decisions

1. **No Framework**: Use vanilla JavaScript for simplicity and no build step
2. **Modular JS**: Separate files for each page/component
3. **CSS Organization**: Separate files by purpose
4. **Local Storage**: Store JWT token and user info
5. **Polling**: Use setInterval for real-time updates (5s for running operations)
6. **Form Validation**: Client-side validation before API calls
7. **Error Handling**: User-friendly error messages
8. **Responsive**: Mobile-first approach

## File Creation Order

1. Folder structure
2. config.js and utils.js (foundation)
3. api.js and auth.js (core)
4. HTML files (structure)
5. CSS files (styling)
6. Page JavaScript files (functionality)
7. Component JavaScript files (reusability)
8. README.md (documentation)

## Testing Checklist

- [ ] All pages load correctly
- [ ] Authentication flow works
- [ ] API calls succeed
- [ ] Error handling works
- [ ] Forms validate correctly