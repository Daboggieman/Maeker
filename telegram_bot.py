import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from manager import JobManager

# Load env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def check_auth(update: Update) -> bool:
    """Ensure the user is authorized."""
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = str(update.effective_user.id)
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            f"Welcome to Maker Studio! Your ID ({user_id}) is authorized.\n\n"
            "Use /job <Topic> to start a new job.\n"
            "Use /resume <Job ID> to resume a failed job."
        )
    else:
        await update.message.reply_text(
            f"Unauthorized. Your ID is {user_id}. Add this to TELEGRAM_ADMIN_ID in .env."
        )

async def run_job_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger the JobManager pipeline."""
    if not await check_auth(update):
        return

    topic = " ".join(context.args) if context.args else ""
    if not topic:
        await update.message.reply_text("Please provide a topic. Example: /job The Fall of Rome")
        return

    chat_id = update.effective_chat.id
    
    # Status callback for Manager to stream logs
    async def send_status(msg):
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"⏳ {msg}")
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")

    await update.message.reply_text(f"🚀 Starting job for topic: {topic}")
    
    manager = JobManager(status_callback=send_status)
    
    try:
        result = await manager.run_job(
            topic=topic,
            category="General",
            produce=True,
            upload=False,
            platform="youtube_short"
        )
        
        if result.get("status") == "Error":
            await update.message.reply_text(f"❌ Job Failed: {result.get('message')}")
        else:
            video_file = result.get("video_file")
            if video_file and os.path.exists(video_file):
                await update.message.reply_text("✅ Video generated! Uploading to Telegram...")
                with open(video_file, 'rb') as video:
                    await context.bot.send_video(chat_id=chat_id, video=video)
            else:
                await update.message.reply_text("✅ Job completed, but video file not found.")
                
    except Exception as e:
        await update.message.reply_text(f"❌ Critical error during job: {e}")

async def resume_job_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resume a failed job."""
    if not await check_auth(update):
        return

    job_id = " ".join(context.args) if context.args else ""
    if not job_id:
        await update.message.reply_text("Please provide a Job ID. Example: /resume 1234abcd")
        return

    chat_id = update.effective_chat.id
    
    async def send_status(msg):
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"⏳ {msg}")
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")

    await update.message.reply_text(f"🚀 Resuming job: {job_id}")
    
    manager = JobManager(status_callback=send_status)
    
    try:
        result = await manager.resume_job(
            job_id=job_id,
            produce=True,
            upload=False,
            platform="youtube_short"
        )
        
        if result.get("status") == "Error":
            await update.message.reply_text(f"❌ Resume Failed: {result.get('message')}")
        else:
            video_file = result.get("video_file")
            if video_file and os.path.exists(video_file):
                await update.message.reply_text("✅ Video generated! Uploading to Telegram...")
                with open(video_file, 'rb') as video:
                    await context.bot.send_video(chat_id=chat_id, video=video)
            else:
                await update.message.reply_text("✅ Job resumed and completed, but video file not found.")
                
    except Exception as e:
        await update.message.reply_text(f"❌ Critical error during resume: {e}")

def main() -> None:
    """Start the bot."""
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        return
        
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("job", run_job_cmd))
    application.add_handler(CommandHandler("resume", resume_job_cmd))

    print("🤖 Telegram Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
