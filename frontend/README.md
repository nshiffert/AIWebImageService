# AI Web Image Service - Frontend

Modern React frontend for the AI Web Image Service, built with TypeScript, Vite, and TailwindCSS.

## Features

- **Public Homepage**: Search and browse AI-generated images with semantic vector search
- **Admin Dashboard**: View system statistics and metrics
- **Image Generation**: Single and bulk image generation with OpenAI GPT Image
- **Review Workflow**: Approve/reject images with bulk selection
- **Settings**: Configure meta prompt for consistent generation style

## Tech Stack

- React 18
- TypeScript
- Vite
- TailwindCSS
- React Router
- Axios
- React Icons

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Create .env file from example
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at http://localhost:5173

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=test-key-local-dev-only
```

## Development

### Project Structure

```
src/
├── api/           # API client and service functions
├── components/    # Reusable UI components
├── context/       # React context providers (Auth)
├── pages/         # Page components
├── types/         # TypeScript type definitions
└── utils/         # Utility functions
```

### Key Pages

- `/` - Public homepage with image search
- `/login` - Admin login (credentials: admin/admin)
- `/admin` - Admin dashboard
- `/admin/generate` - Single and bulk image generation
- `/admin/review` - Review and approval workflow
- `/admin/settings` - Meta prompt configuration

### Authentication

For local development, the app uses simple localStorage-based authentication:
- Username: `admin`
- Password: `admin`

The auth token is stored in localStorage and sent with admin API requests.

## Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## API Integration

The frontend communicates with the backend API using Axios. All API calls are defined in `src/api/client.ts`.

### API Endpoints Used

- `POST /api/v1/search` - Search images by text query
- `GET /health` - Health check
- `POST /api/admin/generate` - Generate single image
- `POST /api/admin/generate/batch` - Generate bulk images
- `GET /api/admin/images/review` - Get review queue
- `POST /api/admin/images/{id}/approve` - Approve image
- `DELETE /api/admin/images/{id}` - Delete image
- `GET /api/admin/stats` - Get system statistics

## Styling

The app uses TailwindCSS for styling. Configuration is in `tailwind.config.js`.

Custom styles and Tailwind directives are in `src/index.css`.
