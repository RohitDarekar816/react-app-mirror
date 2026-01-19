#!/usr/bin/env python3
"""
RocketChat webhook utility for Code Review Agent
Formats and sends code review results to RocketChat channel
"""

import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional


class RocketChatNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def format_code_review_message(self, review_data: Dict[str, Any], repo_name: Optional[str] = None, branch_name: Optional[str] = None) -> Dict[str, Any]:
        """Format code review results for RocketChat message"""
        
        summary = review_data.get('summary', {})
        issues = review_data.get('issues', [])
        suggestions = review_data.get('suggestions', [])
        approved = review_data.get('approved', False)
        
        # Count issues by severity
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        high_issues = [i for i in issues if i.get('severity') == 'high']
        
        # Build message text
        repo_info = f" in {repo_name}" if repo_name else ""
        branch_info = f" on branch `{branch_name}`" if branch_name else ""
        
        header = f"🔍 **Code Review Report{repo_info}{branch_info}**"
        
        # Summary section
        score_emoji = "✅" if summary.get('overall_score', 0) >= 7 else "⚠️" if summary.get('overall_score', 0) >= 5 else "❌"
        approval_emoji = "✅" if approved else "❌"
        
        summary_text = f"""
**Summary:**
{score_emoji} Overall Score: {summary.get('overall_score', 0)}/10
{approval_emoji} Status: {'Approved' if approved else 'Changes Required'}
📁 Files Reviewed: {summary.get('files_reviewed', 0)}
🔢 Total Issues: {summary.get('total_issues', 0)}

🚨 Critical: {summary.get('critical_issues', 0)}
🔴 High: {summary.get('high_issues', 0)}
🟡 Medium: {summary.get('medium_issues', 0)}
🟢 Low: {summary.get('low_issues', 0)}"""
        
        # Critical issues section
        critical_text = ""
        if critical_issues:
            critical_text = "\n\n🚨 **Critical Issues:**\n"
            for issue in critical_issues[:3]:  # Limit to first 3
                critical_text += f"• **{issue.get('title', 'Unknown')}** ({issue.get('file', 'unknown')}:{issue.get('line', '?')})\n"
                critical_text += f"  {issue.get('description', 'No description')}\n"
        
        # High priority issues section
        high_text = ""
        if high_issues:
            high_text = "\n\n🔴 **High Priority Issues:**\n"
            for issue in high_issues[:3]:  # Limit to first 3
                high_text += f"• **{issue.get('title', 'Unknown')}** ({issue.get('file', 'unknown')}:{issue.get('line', '?')})\n"
                high_text += f"  {issue.get('description', 'No description')}\n"
        
        # Suggestions section
        suggestions_text = ""
        if suggestions:
            suggestions_text = f"\n\n💡 **Suggestions:** {len(suggestions)} improvement suggestions available"
        
        # Combine all sections
        full_message = f"{header}{summary_text}{critical_text}{high_text}{suggestions_text}"
        
        # Create RocketChat payload
        payload = {
            "text": full_message,
            "alias": "Code Review Bot",
            "emoji": ":robot_face:",
            "attachments": []
        }
        
        # Add attachment with full details
        if issues or suggestions:
            attachment = {
                "title": "Detailed Code Review Results",
                "title_link": "#",  # Could link to PR/commit
                "text": f"Found {len(issues)} issues and {len(suggestions)} suggestions",
                "fields": [],
                "color": "good" if approved else "warning" if high_issues else "danger"
            }
            
            # Add severity breakdown as fields
            attachment["fields"].extend([
                {"title": "Critical Issues", "value": str(len(critical_issues)), "short": True},
                {"title": "High Issues", "value": str(len(high_issues)), "short": True},
                {"title": "Medium Issues", "value": str(summary.get('medium_issues', 0)), "short": True},
                {"title": "Low Issues", "value": str(summary.get('low_issues', 0)), "short": True}
            ])
            
            payload["attachments"].append(attachment)
        
        return payload
    
    def send_notification(self, review_data: Dict[str, Any], repo_name: Optional[str] = None, branch_name: Optional[str] = None) -> bool:
        """Send code review notification to RocketChat"""
        try:
            payload = self.format_code_review_message(review_data, repo_name, branch_name)
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ RocketChat notification sent successfully")
                return True
            else:
                print(f"❌ Failed to send RocketChat notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending RocketChat notification: {str(e)}")
            return False


def format_webhook_payload(review_data: Dict[str, Any], repo_name: Optional[str] = None, branch_name: Optional[str] = None, webhook_url: Optional[str] = None) -> str:
    """Format webhook payload as JSON string - this is what the agent will use"""
    import os
    webhook_url = webhook_url or os.getenv('ROCKETCHAT_WEBHOOK_URL')
    if not webhook_url:
        raise ValueError("RocketChat webhook URL is required")
    
    notifier = RocketChatNotifier(webhook_url)
    payload = notifier.format_code_review_message(review_data, repo_name, branch_name)
    return json.dumps(payload, indent=2)


def send_webhook_notification(review_data: Dict[str, Any], repo_name: Optional[str] = None, branch_name: Optional[str] = None, webhook_url: Optional[str] = None) -> bool:
    """Send webhook notification - this is what the agent will call"""
    import os
    webhook_url = webhook_url or os.getenv('ROCKETCHAT_WEBHOOK_URL')
    if not webhook_url:
        print("❌ RocketChat webhook URL not provided")
        return False
    
    try:
        notifier = RocketChatNotifier(webhook_url)
        return notifier.send_notification(review_data, repo_name, branch_name)
    except Exception as e:
        print(f"❌ Error sending RocketChat notification: {str(e)}")
        return False


# Example usage for testing
if __name__ == "__main__":
    import sys
    import json
    
    # Parse command line arguments
    if len(sys.argv) < 4:
        print("Usage: python3 rocketchat_webhook.py <action> <review_json> <repo_name> <branch_name> [webhook_url]")
        print("Actions: format_webhook_payload, send_webhook_notification")
        sys.exit(1)
    
    action = sys.argv[1]
    review_json_str = sys.argv[2]
    repo_name = sys.argv[3] if len(sys.argv) > 3 else None
    branch_name = sys.argv[4] if len(sys.argv) > 4 else None
    webhook_url = sys.argv[5] if len(sys.argv) > 5 else None
    
    try:
        review_data = json.loads(review_json_str)
        
        if action == "format_webhook_payload":
            result = format_webhook_payload(review_data, repo_name, branch_name, webhook_url)
            print(result)
        elif action == "send_webhook_notification":
            success = send_webhook_notification(review_data, repo_name, branch_name, webhook_url)
            if success:
                print("✅ RocketChat notification sent successfully")
            else:
                print("❌ Failed to send RocketChat notification")
        else:
            print(f"Unknown action: {action}")
            sys.exit(1)
            
    except json.JSONDecodeError:
        print("❌ Invalid JSON provided")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)