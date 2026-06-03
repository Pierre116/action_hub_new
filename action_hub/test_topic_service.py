#!/usr/bin/env python3
"""Test business-theme service with updated dual-key support."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the database connection
import sqlite3
from unittest.mock import patch, MagicMock

# Import the service functions
from actionhub.admin.topic_service import create_business_theme, update_business_theme

def test_create_business_theme_with_name():
    """Test create_business_theme with 'name' key."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.execute.return_value = mock_cursor
    mock_cursor.lastrowid = 1
    mock_db.commit.return_value = None
    # Mock fetchone for uniqueness check (no duplicate)
    mock_db.execute.return_value.fetchone.return_value = None
    # Mock fetchone for select after insert
    mock_row = {'top_id': 1, 'top_name': 'Test Theme', 'top_desc': None, 'top_active': 1}
    mock_db.execute.return_value.fetchone.return_value = mock_row
    
    with patch('actionhub.admin.topic_service.get_db', return_value=mock_db):
        result = create_business_theme({'name': 'Test Theme'}, actor_id=1)
        assert result['top_name'] == 'Test Theme'
        print("✓ create with 'name' works")

def test_create_business_theme_with_top_name():
    """Test create_business_theme with 'top_name' key (backward compatibility)."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.execute.return_value = mock_cursor
    mock_cursor.lastrowid = 2
    mock_db.commit.return_value = None
    mock_db.execute.return_value.fetchone.return_value = None
    mock_row = {'top_id': 2, 'top_name': 'Legacy Theme', 'top_desc': None, 'top_active': 1}
    mock_db.execute.return_value.fetchone.return_value = mock_row
    
    with patch('actionhub.admin.topic_service.get_db', return_value=mock_db):
        result = create_business_theme({'top_name': 'Legacy Theme'}, actor_id=1)
        assert result['top_name'] == 'Legacy Theme'
        print("✓ create with 'top_name' works")

def test_update_business_theme_with_name():
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.side_effect = [
        {'top_id': 1, 'top_name': 'Old'},  # existing topic
        None,  # duplicate check
        {'top_id': 1, 'top_name': 'New', 'top_active': 1}  # after update
    ]
    mock_db.commit.return_value = None
    
    with patch('actionhub.admin.topic_service.get_db', return_value=mock_db):
        result = update_business_theme(1, {'name': 'New'}, actor_id=1)
        assert result['top_name'] == 'New'
        print("✓ update with 'name' works")

def test_update_business_theme_with_top_name():
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.side_effect = [
        {'top_id': 1, 'top_name': 'Old'},
        None,
        {'top_id': 1, 'top_name': 'New', 'top_active': 1}
    ]
    
    with patch('actionhub.admin.topic_service.get_db', return_value=mock_db):
        result = update_business_theme(1, {'top_name': 'New'}, actor_id=1)
        assert result['top_name'] == 'New'
        print("✓ update with 'top_name' works")

if __name__ == '__main__':
    test_create_business_theme_with_name()
    test_create_business_theme_with_top_name()
    test_update_business_theme_with_name()
    test_update_business_theme_with_top_name()
    print("All dual-key tests passed.")