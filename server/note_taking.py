import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo

class NoteTaking:
    def __init__(self, notes_file: str = "notes.json"):
        """Initialize the note-taking system with the specified JSON file"""
        self.notes_file = notes_file
        self.timezone = ZoneInfo('Asia/Kolkata')
        self._ensure_notes_file()

    def _ensure_notes_file(self) -> None:
        """Ensure the notes file exists and has valid JSON structure"""
        if not os.path.exists(self.notes_file):
            # Create new file with empty notes list
            self._write_notes([])
        else:
            # Verify existing file has valid JSON structure
            try:
                with open(self.notes_file, 'r') as f:
                    notes = json.load(f)
                if not isinstance(notes, list):
                    # If file exists but has invalid structure, reset it
                    self._write_notes([])
            except json.JSONDecodeError:
                # If file exists but is not valid JSON, reset it
                self._write_notes([])

    def _read_notes(self) -> List[Dict[str, Any]]:
        """Read notes from the JSON file"""
        try:
            with open(self.notes_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading notes file: {str(e)}")
            return []

    def _write_notes(self, notes: List[Dict[str, Any]]) -> bool:
        """Write notes to the JSON file"""
        try:
            with open(self.notes_file, 'w') as f:
                json.dump(notes, f, indent=2)
            return True
        except Exception as e:
            print(f"Error writing to notes file: {str(e)}")
            return False

    def _get_current_time(self) -> str:
        """Get current time in IST format"""
        return datetime.now(self.timezone).isoformat()

    def add_note(self, note_name: str, content: str) -> Dict[str, Any]:
        """
        Add a new note or update an existing one
        
        Args:
            note_name: Name of the note (required)
            content: Content of the note (required)
            
        Returns:
            Dict containing success status and message
        """
        try:
            # Validate inputs
            if not note_name or not isinstance(note_name, str):
                return {
                    "success": False,
                    "message": "Note name is required and must be a string",
                    "note": None
                }
            
            if not content or not isinstance(content, str):
                return {
                    "success": False,
                    "message": "Content is required and must be a string",
                    "note": None
                }
            
            # Read existing notes
            notes = self._read_notes()
            
            # Check if note with same name exists
            note_exists = False
            for note in notes:
                if note.get('note_name') == note_name:
                    # Update existing note
                    note['content'] = content
                    note['updated_at'] = self._get_current_time()
                    note_exists = True
                    break
            
            if not note_exists:
                # Add new note
                new_note = {
                    'note_name': note_name,
                    'content': content,
                    'created_at': self._get_current_time(),
                    'updated_at': self._get_current_time()
                }
                notes.append(new_note)
            
            # Write updated notes back to file
            if self._write_notes(notes):
                return {
                    "success": True,
                    "message": "Note updated successfully" if note_exists else "Note created successfully",
                    "note": {
                        'note_name': note_name,
                        'content': content,
                        'updated_at': self._get_current_time()
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to save note",
                    "note": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error adding note: {str(e)}",
                "note": None
            }

    def get_note(self, note_name: str) -> Dict[str, Any]:
        """
        Get a specific note by name
        
        Args:
            note_name: Name of the note to retrieve
            
        Returns:
            Dict containing success status and note data
        """
        try:
            notes = self._read_notes()
            for note in notes:
                if note.get('note_name') == note_name:
                    return {
                        "success": True,
                        "message": "Note found",
                        "note": note
                    }
            
            return {
                "success": False,
                "message": f"No note found with name: {note_name}",
                "note": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving note: {str(e)}",
                "note": None
            }

    def get_all_notes(self) -> Dict[str, Any]:
        """
        Get all notes
        
        Returns:
            Dict containing success status and list of all notes
        """
        try:
            notes = self._read_notes()
            return {
                "success": True,
                "message": f"Found {len(notes)} notes",
                "notes": notes
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving notes: {str(e)}",
                "notes": None
            }

    def delete_note(self, note_name: str) -> Dict[str, Any]:
        """
        Delete a note by name
        
        Args:
            note_name: Name of the note to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            notes = self._read_notes()
            initial_length = len(notes)
            
            # Filter out the note to delete
            notes = [note for note in notes if note.get('note_name') != note_name]
            
            if len(notes) == initial_length:
                return {
                    "success": False,
                    "message": f"No note found with name: {note_name}",
                    "deleted_note": None
                }
            
            if self._write_notes(notes):
                return {
                    "success": True,
                    "message": f"Note '{note_name}' deleted successfully",
                    "deleted_note": note_name
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to save notes after deletion",
                    "deleted_note": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting note: {str(e)}",
                "deleted_note": None
            }

def main():
    """Example usage of the NoteTaking class"""
    note_taker = NoteTaking()
    
    # Add a new note
    result = note_taker.add_note(
        note_name="Meeting Notes",
        content="Discussed project timeline and deliverables"
    )
    print("\nAdding note:", result)
    
    # Get the note
    result = note_taker.get_note("Meeting Notes")
    print("\nGetting note:", result)
    
    # Update the note
    result = note_taker.add_note(
        note_name="Meeting Notes",
        content="Updated: Added new tasks and deadlines"
    )
    print("\nUpdating note:", result)
    
    # Get all notes
    result = note_taker.get_all_notes()
    print("\nAll notes:", result)
    
    # Delete the note
    result = note_taker.delete_note("Meeting Notes")
    print("\nDeleting note:", result)

if __name__ == "__main__":
    main()
