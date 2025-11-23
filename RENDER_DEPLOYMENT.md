# Deploying to Render.com

This guide will help you deploy the MidOpen Financial Prediction Dashboard to Render.com.

## Prerequisites

- A Render.com account (free tier available)
- Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)

## Overview

The application has been updated to support PostgreSQL database storage, making it compatible with Render.com's cloud environment. It will automatically use PostgreSQL when the `DATABASE_URL` environment variable is present, or fall back to JSON file storage for local development.

## Deployment Steps

### Step 1: Create a PostgreSQL Database

1. Log in to your [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** and select **"PostgreSQL"**
3. Configure your database:
   - **Name**: `midopen-db` (or any name you prefer)
   - **Database**: `midopen`
   - **User**: (auto-generated)
   - **Region**: Choose closest to your users
   - **PostgreSQL Version**: 15 or higher
   - **Plan**: **Free** (expires after 90 days) or **Starter** ($7/month for persistence)
4. Click **"Create Database"**
5. Wait for the database to be created (takes ~2 minutes)
6. **Save the Internal Database URL** - you'll need this in Step 2

### Step 2: Create a Web Service

1. From the Render Dashboard, click **"New +"** and select **"Web Service"**
2. Connect your Git repository:
   - If not connected, authorize Render to access your repository
   - Select the repository containing your MidOpen code
3. Configure your web service:
   - **Name**: `midopen-dashboard` (or any name you prefer)
   - **Region**: Same as your database
   - **Branch**: `main` (or your deployment branch)
   - **Root Directory**: Leave blank (unless your code is in a subdirectory)
   - **Runtime**: **Python 3**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run Home.py --server.port=$PORT --server.address=0.0.0.0`
   - **Plan**: **Free** (sleeps after 15 min) or **Starter** ($7/month for always-on)

### Step 3: Add Environment Variables

1. Scroll down to the **"Environment Variables"** section
2. Click **"Add Environment Variable"**
3. Add the following variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Paste the **Internal Database URL** from Step 1
     - Format: `postgresql://user:password@hostname/database`
     - Example: `postgresql://midopen_user:abc123@dpg-xyz.oregon-postgres.render.com/midopen`

4. Click **"Add Environment Variable"** again (optional but recommended):
   - **Key**: `PYTHONUNBUFFERED`
   - **Value**: `1`
   - (This ensures logs appear in real-time)

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start the Streamlit application
   - Connect to your PostgreSQL database
3. Monitor the deployment logs in real-time
4. Once deployed, you'll see **"Your service is live 🎉"**
5. Click the URL (e.g., `https://midopen-dashboard.onrender.com`) to access your app

## Post-Deployment

### Verify Database Connection

1. Open your deployed application
2. Upload a CSV file and run an analysis
3. Check "View History" mode to ensure predictions are being saved
4. If you see your saved predictions, PostgreSQL is working correctly!

### Check Logs

If something goes wrong:
1. Go to your Web Service dashboard
2. Click **"Logs"** tab
3. Look for any errors related to database connection or initialization
4. Common issues:
   - **`DATABASE_URL` not set**: Check environment variables
   - **Database connection failed**: Verify the database URL is correct
   - **Table creation failed**: Check database permissions

## Free Tier Limitations

### PostgreSQL Free Tier
- ✅ **Storage**: 1 GB (plenty for this app - you're using ~28 KB)
- ✅ **Expires**: After 90 days
- ⚠️ **After expiration**: Database and all data are **permanently deleted**
- 💡 **Recommendation**: Upgrade to Starter ($7/month) before 90 days if you need persistent data

### Web Service Free Tier
- ✅ **Always available**: Yes
- ⚠️ **Sleeps**: After 15 minutes of inactivity
- ⚠️ **Wake-up time**: 30-60 seconds on first request after sleep
- ⚠️ **No scheduled jobs**: Background jobs won't run while sleeping
- 💡 **Recommendation**: Upgrade to Starter ($7/month) for always-on service

### Total Cost Summary

| Tier | Database | Web Service | Total/Month | Notes |
|------|----------|-------------|-------------|-------|
| **Free** | $0 | $0 | **$0** | DB expires in 90 days, service sleeps |
| **Basic** | $7 | $0 | **$7/month** | Persistent DB, service sleeps |
| **Production** | $7 | $7 | **$14/month** | Persistent DB, always-on |

## Local Development

To run locally without PostgreSQL:

```bash
# Don't set DATABASE_URL - app will use JSON storage
python -m streamlit run Home.py
```

To test PostgreSQL locally:

```bash
# Install PostgreSQL locally
# Create a database: createdb midopen

# Set environment variable
export DATABASE_URL=postgresql://username:password@localhost:5432/midopen

# Run the app
python -m streamlit run Home.py
```

## Migrating Existing Data

If you have existing JSON predictions in `data/prediction_history/`:

1. The app will **not** automatically migrate existing JSON files to PostgreSQL
2. Old predictions will remain in JSON files (not visible when using PostgreSQL)
3. New predictions will be saved to PostgreSQL
4. To migrate manually, you would need to write a migration script (not included)

## Troubleshooting

### "DATABASE_URL environment variable is required"

**Solution**: Make sure you added `DATABASE_URL` to your environment variables in Render.

### "Could not connect to PostgreSQL database"

**Solutions**:
1. Verify the `DATABASE_URL` is correct (copy from PostgreSQL service internal URL)
2. Ensure both services are in the same region
3. Use the **Internal Database URL**, not the External URL
4. Wait 2-3 minutes after database creation before deploying web service

### "Table does not exist"

**Solution**: The app should auto-create tables. If not:
1. Check database permissions
2. Verify PostgreSQL version is 12+
3. Check logs for initialization errors

### Application is slow to wake up

**Solution**: This is normal for free tier. Upgrade to Starter ($7/month) for always-on service.

## Support

For issues:
- Check Render [status page](https://status.render.com/)
- Review Render [documentation](https://render.com/docs)
- Check application logs in Render dashboard

## Architecture Notes

### Storage Backend Selection

The application automatically selects the storage backend:

```python
# If DATABASE_URL is set → PostgreSQL
if os.getenv('DATABASE_URL'):
    backend = PostgreSQLStorageBackend()
# Otherwise → JSON files
else:
    backend = JSONStorageBackend()
```

### Database Schema

PostgreSQL table structure:

```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    instrument VARCHAR(50),
    data_timestamp TIMESTAMP,
    analysis_timestamp TIMESTAMP,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- **JSONB storage**: Full prediction data stored as JSON for flexibility
- **Indexed columns**: `instrument`, `data_timestamp`, `key` for fast queries
- **Timestamps**: Track when predictions were created and updated

---

**Need help?** Check the logs first, then review Render's documentation.
