"""Open one Outlook mail item by EntryID — Windows side, invoked via
powershell python (same bridge as the collector). Read-only: Display() only."""
import sys

sys.stdout.reconfigure(encoding="utf-8")
import win32com.client

entry_id = sys.argv[1]
ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
item = ns.GetItemFromID(entry_id)
item.Display()
print("OK")
