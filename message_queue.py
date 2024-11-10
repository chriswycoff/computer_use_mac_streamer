# message_queue.py
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

class MessageQueue:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

    def send_message(self, content: str, sender: str, recipient: str):
        """Send a message to the queue"""
        data = {
            "content": content,
            "sender": sender,
            "recipient": recipient,
            "is_read": False
        }
        
        response = self.supabase.table("messages").insert(data).execute()
        return response.data[0]

    def get_unread_messages(self, recipient: str):
        """Get all unread messages for a specific recipient"""
        response = self.supabase.table("messages")\
            .select("*")\
            .eq("recipient", recipient)\
            .eq("is_read", False)\
            .order("created_at")\
            .execute()
        
        return response.data

    def mark_as_read(self, message_id: str):
        """Mark a specific message as read"""
        now = datetime.now(pytz.UTC)
        data = {
            "is_read": True,
            "read_at": now.isoformat()
        }
        
        response = self.supabase.table("messages")\
            .update(data)\
            .eq("id", message_id)\
            .execute()
        
        return response.data[0]

    def mark_all_as_read(self, recipient: str):
        """Mark all messages for a recipient as read"""
        now = datetime.now(pytz.UTC)
        data = {
            "is_read": True,
            "read_at": now.isoformat()
        }
        
        response = self.supabase.table("messages")\
            .update(data)\
            .eq("recipient", recipient)\
            .eq("is_read", False)\
            .execute()
        
        return response.data

if __name__ == "__main__":

    mq = MessageQueue()
    do_messages = False
    if do_messages:
        for i in range(5):
            # Test sending a message
            try:
                message = mq.send_message(
                    content="Hello, this is a test message",
                    sender="user",
                    recipient="agent"
                )
                print(f"Sent message: {message}")
            except Exception as e:
                print(f"Error sending message: {e}")
        
    # Test getting unread messages
    try:
        unread = mq.get_unread_messages("agent")
        # print(f"Unread messages: {unread}")
        print(f"Unread messages: {len(unread)}")
        for message in unread:
            print(f"Unread message: {message}")
    except Exception as e:
        print(f"Error getting unread messages: {e}")
    
    # Test marking a message as read
    try:
        if unread:
            marked = mq.mark_as_read(unread[0]['id'])
            print(f"Marked message as read: {marked}")
    except Exception as e:
        print(f"Error marking message as read: {e}")