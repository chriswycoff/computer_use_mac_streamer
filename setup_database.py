# setup_database.py
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Load Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_table():
    """Create the messages table if it doesn't exist"""
    try:
        # Using REST API to create table via Supabase functions
        response = supabase.rpc(
            'create_messages_table',
            {}
        ).execute()
        print("Table created successfully or already exists!")
        return True
    except Exception as e:
        print(f"Error creating table: {e}")
        print("Please run the following SQL in your Supabase SQL editor:")
        print("""
        -- First, create the function to create the table
        create or replace function create_messages_table()
        returns void as $$
        begin
            create table if not exists messages (
                id uuid default uuid_generate_v4() primary key,
                content text not null,
                sender varchar(255) not null,
                recipient varchar(255) not null,
                created_at timestamp with time zone default current_timestamp,
                read_at timestamp with time zone,
                is_read boolean default false
            );
        end;
        $$ language plpgsql security definer;
        
        -- Then call the function to create the table
        select create_messages_table();
        """)
        return False

def test_connection():
    """Test the connection"""
    try:
        response = supabase.table('messages').select("*").limit(1)
        print("Successfully connected to Supabase!")
        return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Supabase connection...")
    if test_connection():
        print("Creating messages table...")
        create_table()