# Forex Factory Scraper - VPS Deployment & Convex Integration Plan

## Current Project Status

Your scraper is **NOT ready** for VPS deployment as-is. Here are the key issues:

### Issues Identified
1. **No Web Interface**
   - Current scraper runs as a CLI script only
   - Not callable from outside without containerization + web wrapper

2. **File-based Output Only**
   - Currently saves to local CSV files in `/news` directory
   - No Convex database integration

3. **Missing Infrastructure Files**
   - No Dockerfile for containerization
   - No web server/API endpoints
   - No environment configuration for deployment

## Required Modifications

### Phase 1: Web API Wrapper
1. **Create Flask/FastAPI wrapper** (`app.py`)
   - Add `/scrape` endpoint to trigger scraping
   - Add `/scrape/{month}` endpoint for specific months
   - Add `/health` endpoint for monitoring
   - Add `/status` endpoint to check scraping status
   - Add error handling and logging

### Phase 2: Convex Integration
2. **Install Convex Python SDK**
   ```bash
   pip install convex python-dotenv
   ```

3. **Create Convex client module** (`convex_client.py`)
   - Initialize client with deployment URL from environment
   - Add function to save scraped data to Convex database
   - Add data validation and transformation functions
   - Handle authentication if required

4. **Modify existing code**
   - Update `utils.py` to optionally save to Convex instead of CSV
   - Add environment variable support for Convex URL
   - Maintain backward compatibility with CSV output

### Phase 3: Containerization
5. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim

   # Install Chrome and dependencies for Selenium
   RUN apt-get update && apt-get install -y \
       wget \
       gnupg \
       unzip \
       && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
       && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
       && apt-get update \
       && apt-get install -y google-chrome-stable

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .

   EXPOSE 8000
   CMD ["python", "app.py"]
   ```

6. **Add environment configuration**
   - Create `.env.example` with required variables
   - Add `docker-compose.yml` for local testing
   - Update `requirements.txt` with web framework dependencies

### Phase 4: Dokploy Deployment
7. **Deploy to Dokploy VPS**
   - Configure container with environment variables:
     - `CONVEX_URL`: Your Convex deployment URL
     - `TARGET_TIMEZONE`: Timezone for data conversion
     - `ALLOWED_CURRENCY_CODES`: Currency filtering
     - `ALLOWED_IMPACT_COLORS`: Impact level filtering

8. **Set up scheduled tasks in Dokploy**
   - Create monthly cron job: `0 0 1 * *` (1st day of each month)
   - Configure HTTP endpoint trigger for manual execution
   - Set up monitoring and error notifications

### Phase 5: Integration with Next.js App
9. **API Integration**
   - Add webhook endpoints for triggering from Next.js
   - Implement authentication between services (API keys)
   - Add status monitoring endpoints
   - Create data synchronization endpoints

10. **Next.js Integration**
    - Add API calls to trigger scraping from your Next.js app
    - Set up data fetching from Convex in your frontend
    - Add admin interface for manual scraping triggers

## Implementation Checklist

### Backend Modifications
- [ ] Create Flask/FastAPI web wrapper
- [ ] Install and configure Convex Python SDK
- [ ] Create Convex client module
- [ ] Modify utils.py for database integration
- [ ] Create Dockerfile and docker-compose
- [ ] Add environment variable support
- [ ] Test containerized application locally

### Deployment Setup
- [ ] Configure Dokploy project
- [ ] Set environment variables in Dokploy
- [ ] Deploy container to VPS
- [ ] Configure scheduled tasks/cron jobs
- [ ] Test external API accessibility
- [ ] Set up monitoring and logging

### Integration & Testing
- [ ] Test manual scraping via API
- [ ] Test scheduled execution
- [ ] Verify data storage in Convex
- [ ] Test integration with Next.js app
- [ ] Set up error handling and notifications

## Estimated Timeline
- **Backend modifications**: 4-6 hours
- **Containerization & testing**: 2-3 hours
- **Deployment & configuration**: 2-3 hours
- **Integration testing**: 2-3 hours
- **Total**: 1-2 days for complete implementation

## Key Benefits After Implementation
- ✅ **Schedulable**: Monthly automated execution via cron
- ✅ **Externally Callable**: REST API endpoints for manual triggers
- ✅ **Database Integration**: Data stored in Convex for your Next.js app
- ✅ **Scalable**: Containerized deployment on VPS
- ✅ **Monitorable**: Health checks and status endpoints
- ✅ **Maintainable**: Environment-based configuration