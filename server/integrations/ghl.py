from __future__ import annotations

"""
GoHighLevel API Client - Complete v2 Coverage

Full API client covering ALL GHL API v2 endpoints as documented in:
https://github.com/GoHighLevel/highlevel-api-docs

Base URL: https://services.leadconnectorhq.com
API Version Header: 2021-07-28
Auth: Bearer token (API key or OAuth2 access token)

Endpoint categories covered (ALL 36 GHL API categories):
- OAuth / Auth
- Contacts (CRUD, search, tags, notes, tasks, bulk, followers, campaigns, workflows)
- Conversations / Messages (SMS, Email, inbound, outbound, files, recordings, transcriptions, live-chat)
- Calendars (groups, calendars, events, appointments, block slots, resources, notifications, service bookings)
- Opportunities / Pipelines (CRUD, search, status, followers, upsert)
- Funnels / Websites (list, pages, redirects)
- Forms (list, submissions, file upload)
- Surveys (list, submissions)
- Workflows (list)
- Custom Fields v2 (CRUD, folders, by object key)
- Locations / Sub-Accounts (search, CRUD, tags, tasks, recurring tasks, custom fields, custom values, templates, timezones)
- Emails (campaigns/schedules, builder templates)
- Products (CRUD, prices, inventory, collections, reviews, store stats, bulk edit, display priorities)
- Payments (orders, fulfillments, order notes, transactions, subscriptions, coupons, whitelabel, custom providers)
- Invoices (CRUD, templates, schedules, estimates, text2pay, late fees, payment methods, send, record payment)
- Campaigns (list)
- Blogs (posts, authors, categories)
- Courses (import)
- Media Library (files, folders, upload, bulk)
- Users (search, CRUD)
- Social Media Posting (OAuth, posts, accounts, Google Business)
- Trigger Links (CRUD, search)
- Businesses (CRUD)
- Companies (get)
- Snapshots (list, share, status)
- Associations / Relations (CRUD)
- Conversation AI (agents CRUD, actions, generations)
- Custom Objects (schemas, records CRUD, search)
- Voice AI (agents CRUD, actions CRUD, call logs)
- Store (shipping zones, rates, carriers, settings)
- Custom Menus (CRUD)
- Documents / Proposals (list, send, templates)
- Phone System (number pools, active numbers)
- Email ISV (verification)
- Marketplace / Billing (charges, funds, app installations)
"""

import httpx
import os
from typing import Any


class GHLClient:
    """
    Complete HTTP client for GoHighLevel API v2.
    Every public endpoint is represented as a typed method.
    """

    def __init__(self, api_key: str | None = None, location_id: str | None = None):
        self.base_url = os.getenv("GHL_BASE_URL", "https://services.leadconnectorhq.com")
        self.api_key = api_key or os.getenv("GHL_API_KEY", "")
        self.location_id = location_id or os.getenv("GHL_LOCATION_ID", "")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers=self._build_headers()
        )

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }

    async def request(
        self,
        method: str,
        endpoint: str,
        body: dict | None = None,
        query_params: dict | None = None,
        files: dict | None = None,
    ) -> dict[str, Any]:
        """Generic API request. All convenience methods call this."""
        try:
            kwargs: dict[str, Any] = {
                "method": method.upper(),
                "url": endpoint,
                "params": query_params,
            }
            if files:
                kwargs["files"] = files
                # Remove content-type header so httpx sets multipart boundary
                headers = dict(self._build_headers())
                headers.pop("Content-Type", None)
                kwargs["headers"] = headers
            else:
                kwargs["json"] = body

            response = await self.client.request(**kwargs)
            response.raise_for_status()
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.content else None,
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "status_code": e.response.status_code,
                "error": str(e),
                "response_body": e.response.text,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _loc(self, params: dict | None = None) -> dict:
        """Inject locationId into query params."""
        p = params or {}
        p.setdefault("locationId", self.location_id)
        return p

    def _loc_body(self, body: dict | None = None) -> dict:
        """Inject locationId into request body."""
        b = body or {}
        b.setdefault("locationId", self.location_id)
        return b

    async def close(self):
        await self.client.aclose()

    # =========================================================================
    # OAUTH
    # =========================================================================

    async def get_access_token(self, client_id: str, client_secret: str,
                                grant_type: str, **kwargs) -> dict:
        """POST /oauth/token - Exchange code or refresh token for access token."""
        return await self.request("POST", "/oauth/token", body={
            "client_id": client_id, "client_secret": client_secret,
            "grant_type": grant_type, **kwargs
        })

    async def get_location_token(self, company_id: str, location_id: str) -> dict:
        """POST /oauth/locationToken - Get location token from agency token."""
        return await self.request("POST", "/oauth/locationToken", body={
            "companyId": company_id, "locationId": location_id
        })

    async def get_installed_locations(self, company_id: str, app_id: str,
                                       **kwargs) -> dict:
        """GET /oauth/installedLocations"""
        return await self.request("GET", "/oauth/installedLocations",
                                  query_params={"companyId": company_id,
                                                "appId": app_id, **kwargs})

    # =========================================================================
    # CONTACTS
    # =========================================================================

    async def search_contacts(self, filters: dict) -> dict:
        """POST /contacts/search - Advanced contact search with filters."""
        return await self.request("POST", "/contacts/search",
                                  body=self._loc_body(filters))

    async def search_duplicate_contacts(self, **kwargs) -> dict:
        """GET /contacts/search/duplicate"""
        return await self.request("GET", "/contacts/search/duplicate",
                                  query_params=self._loc(kwargs))

    async def get_contacts(self, query: str | None = None, limit: int = 20,
                            **kwargs) -> dict:
        """GET /contacts/ - List contacts (deprecated, use search_contacts)."""
        params = self._loc({"limit": limit, **kwargs})
        if query:
            params["query"] = query
        return await self.request("GET", "/contacts/", query_params=params)

    async def get_contact(self, contact_id: str) -> dict:
        """GET /contacts/{contactId}"""
        return await self.request("GET", f"/contacts/{contact_id}")

    async def create_contact(self, data: dict) -> dict:
        """POST /contacts/ - Create a new contact."""
        return await self.request("POST", "/contacts/",
                                  body=self._loc_body(data))

    async def upsert_contact(self, data: dict) -> dict:
        """POST /contacts/upsert - Create or update contact."""
        return await self.request("POST", "/contacts/upsert",
                                  body=self._loc_body(data))

    async def update_contact(self, contact_id: str, data: dict) -> dict:
        """PUT /contacts/{contactId}"""
        return await self.request("PUT", f"/contacts/{contact_id}", body=data)

    async def delete_contact(self, contact_id: str) -> dict:
        """DELETE /contacts/{contactId}"""
        return await self.request("DELETE", f"/contacts/{contact_id}")

    async def get_contacts_by_business(self, business_id: str, **kwargs) -> dict:
        """GET /contacts/business/{businessId}"""
        return await self.request("GET", f"/contacts/business/{business_id}",
                                  query_params=kwargs or None)

    # --- Contact Tags ---

    async def add_contact_tags(self, contact_id: str, tags: list[str]) -> dict:
        """POST /contacts/{contactId}/tags"""
        return await self.request("POST", f"/contacts/{contact_id}/tags",
                                  body={"tags": tags})

    async def remove_contact_tags(self, contact_id: str, tags: list[str]) -> dict:
        """DELETE /contacts/{contactId}/tags"""
        return await self.request("DELETE", f"/contacts/{contact_id}/tags",
                                  body={"tags": tags})

    async def bulk_update_tags(self, update_type: str, data: dict) -> dict:
        """POST /contacts/bulk/tags/update/{type} - type: add or remove."""
        return await self.request("POST",
                                  f"/contacts/bulk/tags/update/{update_type}",
                                  body=data)

    # --- Contact Notes ---

    async def get_contact_notes(self, contact_id: str) -> dict:
        """GET /contacts/{contactId}/notes"""
        return await self.request("GET", f"/contacts/{contact_id}/notes")

    async def create_contact_note(self, contact_id: str, body: str,
                                   user_id: str | None = None) -> dict:
        """POST /contacts/{contactId}/notes"""
        data: dict[str, Any] = {"body": body}
        if user_id:
            data["userId"] = user_id
        return await self.request("POST", f"/contacts/{contact_id}/notes",
                                  body=data)

    async def update_contact_note(self, contact_id: str, note_id: str,
                                   body: str) -> dict:
        """PUT /contacts/{contactId}/notes/{noteId}"""
        return await self.request("PUT",
                                  f"/contacts/{contact_id}/notes/{note_id}",
                                  body={"body": body})

    async def delete_contact_note(self, contact_id: str, note_id: str) -> dict:
        """DELETE /contacts/{contactId}/notes/{noteId}"""
        return await self.request("DELETE",
                                  f"/contacts/{contact_id}/notes/{note_id}")

    # --- Contact Tasks ---

    async def get_contact_tasks(self, contact_id: str) -> dict:
        """GET /contacts/{contactId}/tasks"""
        return await self.request("GET", f"/contacts/{contact_id}/tasks")

    async def create_contact_task(self, contact_id: str, data: dict) -> dict:
        """POST /contacts/{contactId}/tasks"""
        return await self.request("POST", f"/contacts/{contact_id}/tasks",
                                  body=data)

    async def update_contact_task(self, contact_id: str, task_id: str,
                                   data: dict) -> dict:
        """PUT /contacts/{contactId}/tasks/{taskId}"""
        return await self.request("PUT",
                                  f"/contacts/{contact_id}/tasks/{task_id}",
                                  body=data)

    async def delete_contact_task(self, contact_id: str, task_id: str) -> dict:
        """DELETE /contacts/{contactId}/tasks/{taskId}"""
        return await self.request("DELETE",
                                  f"/contacts/{contact_id}/tasks/{task_id}")

    # --- Contact Appointments ---

    async def get_contact_appointments(self, contact_id: str) -> dict:
        """GET /contacts/{contactId}/appointments"""
        return await self.request("GET",
                                  f"/contacts/{contact_id}/appointments")

    # --- Contact Campaigns ---

    async def add_contact_to_campaign(self, contact_id: str,
                                       campaign_id: str) -> dict:
        """POST /contacts/{contactId}/campaigns/{campaignId}"""
        return await self.request(
            "POST", f"/contacts/{contact_id}/campaigns/{campaign_id}")

    async def remove_contact_from_campaign(self, contact_id: str,
                                            campaign_id: str) -> dict:
        """DELETE /contacts/{contactId}/campaigns/{campaignId}"""
        return await self.request(
            "DELETE", f"/contacts/{contact_id}/campaigns/{campaign_id}")

    # --- Contact Workflows ---

    async def add_contact_to_workflow(self, contact_id: str,
                                       workflow_id: str) -> dict:
        """POST /contacts/{contactId}/workflow/{workflowId}"""
        return await self.request(
            "POST", f"/contacts/{contact_id}/workflow/{workflow_id}")

    async def remove_contact_from_workflow(self, contact_id: str,
                                            workflow_id: str) -> dict:
        """DELETE /contacts/{contactId}/workflow/{workflowId}"""
        return await self.request(
            "DELETE", f"/contacts/{contact_id}/workflow/{workflow_id}")

    # --- Contact Followers ---

    async def add_contact_followers(self, contact_id: str,
                                     followers: list[str]) -> dict:
        """POST /contacts/{contactId}/followers"""
        return await self.request("POST",
                                  f"/contacts/{contact_id}/followers",
                                  body={"followers": followers})

    async def remove_contact_followers(self, contact_id: str,
                                        followers: list[str]) -> dict:
        """DELETE /contacts/{contactId}/followers"""
        return await self.request("DELETE",
                                  f"/contacts/{contact_id}/followers",
                                  body={"followers": followers})

    # --- Contact Bulk ---

    async def bulk_update_contact_business(self, data: dict) -> dict:
        """POST /contacts/bulk/business"""
        return await self.request("POST", "/contacts/bulk/business", body=data)

    # =========================================================================
    # CONVERSATIONS / MESSAGES
    # =========================================================================

    async def search_conversations(self, **kwargs) -> dict:
        """GET /conversations/search"""
        return await self.request("GET", "/conversations/search",
                                  query_params=self._loc(kwargs))

    async def create_conversation(self, contact_id: str) -> dict:
        """POST /conversations/"""
        return await self.request("POST", "/conversations/",
                                  body=self._loc_body({"contactId": contact_id}))

    async def get_conversation(self, conversation_id: str) -> dict:
        """GET /conversations/{conversationId}"""
        return await self.request("GET", f"/conversations/{conversation_id}")

    async def update_conversation(self, conversation_id: str,
                                   data: dict) -> dict:
        """PUT /conversations/{conversationId}"""
        return await self.request("PUT", f"/conversations/{conversation_id}",
                                  body=self._loc_body(data))

    async def delete_conversation(self, conversation_id: str) -> dict:
        """DELETE /conversations/{conversationId}"""
        return await self.request("DELETE",
                                  f"/conversations/{conversation_id}")

    async def send_message(self, contact_id: str, msg_type: str,
                            message: str, **kwargs) -> dict:
        """POST /conversations/messages - Send SMS, Email, etc."""
        body: dict[str, Any] = {
            "type": msg_type, "contactId": contact_id,
            "message": message, **kwargs,
        }
        return await self.request("POST", "/conversations/messages", body=body)

    async def send_sms(self, contact_id: str, message: str) -> dict:
        """Send SMS shortcut."""
        return await self.send_message(contact_id, "SMS", message)

    async def send_email(self, contact_id: str, subject: str,
                          html: str) -> dict:
        """Send Email shortcut."""
        return await self.send_message(
            contact_id, "Email", html, subject=subject)

    async def get_message(self, message_id: str) -> dict:
        """GET /conversations/messages/{id}"""
        return await self.request("GET",
                                  f"/conversations/messages/{message_id}")

    async def get_conversation_messages(self, conversation_id: str,
                                         **kwargs) -> dict:
        """GET /conversations/{conversationId}/messages"""
        return await self.request(
            "GET", f"/conversations/{conversation_id}/messages",
            query_params=kwargs or None)

    async def send_inbound_message(self, data: dict) -> dict:
        """POST /conversations/messages/inbound"""
        return await self.request("POST", "/conversations/messages/inbound",
                                  body=data)

    async def send_outbound_message(self, data: dict) -> dict:
        """POST /conversations/messages/outbound"""
        return await self.request("POST", "/conversations/messages/outbound",
                                  body=data)

    async def cancel_scheduled_message(self, message_id: str) -> dict:
        """DELETE /conversations/messages/{messageId}/schedule"""
        return await self.request(
            "DELETE", f"/conversations/messages/{message_id}/schedule")

    async def update_message_status(self, message_id: str,
                                     status: str) -> dict:
        """PUT /conversations/messages/{messageId}/status"""
        return await self.request(
            "PUT", f"/conversations/messages/{message_id}/status",
            body={"status": status})

    async def upload_conversation_file(self, conversation_id: str,
                                        location_id: str,
                                        attachment_urls: list[str]) -> dict:
        """POST /conversations/messages/upload"""
        return await self.request("POST", "/conversations/messages/upload",
                                  body={"conversationId": conversation_id,
                                        "locationId": location_id,
                                        "attachmentUrls": attachment_urls})

    async def get_email_message(self, email_id: str) -> dict:
        """GET /conversations/messages/email/{id}"""
        return await self.request("GET",
                                  f"/conversations/messages/email/{email_id}")

    # =========================================================================
    # CALENDARS
    # =========================================================================

    # --- Calendar Groups ---

    async def get_calendar_groups(self) -> dict:
        """GET /calendars/groups"""
        return await self.request("GET", "/calendars/groups",
                                  query_params=self._loc())

    async def create_calendar_group(self, data: dict) -> dict:
        """POST /calendars/groups"""
        return await self.request("POST", "/calendars/groups", body=data)

    async def validate_calendar_group_slug(self, data: dict) -> dict:
        """POST /calendars/groups/validate-slug"""
        return await self.request("POST", "/calendars/groups/validate-slug",
                                  body=data)

    async def update_calendar_group(self, group_id: str, data: dict) -> dict:
        """PUT /calendars/groups/{groupId}"""
        return await self.request("PUT", f"/calendars/groups/{group_id}",
                                  body=data)

    async def delete_calendar_group(self, group_id: str) -> dict:
        """DELETE /calendars/groups/{groupId}"""
        return await self.request("DELETE", f"/calendars/groups/{group_id}")

    async def update_calendar_group_status(self, group_id: str,
                                            data: dict) -> dict:
        """PUT /calendars/groups/{groupId}/status"""
        return await self.request("PUT",
                                  f"/calendars/groups/{group_id}/status",
                                  body=data)

    # --- Calendars ---

    async def get_calendars(self, **kwargs) -> dict:
        """GET /calendars/"""
        return await self.request("GET", "/calendars/",
                                  query_params=self._loc(kwargs))

    async def create_calendar(self, data: dict) -> dict:
        """POST /calendars/"""
        return await self.request("POST", "/calendars/", body=data)

    async def create_calendar_notification(self, calendar_id: str, data: dict) -> dict:
        """POST /calendars/{calendarId}/notifications"""
        return await self.request("POST", f"/calendars/{calendar_id}/notifications", body=data)

    async def get_calendar(self, calendar_id: str) -> dict:
        """GET /calendars/{calendarId}"""
        return await self.request("GET", f"/calendars/{calendar_id}")

    async def update_calendar(self, calendar_id: str, data: dict) -> dict:
        """PUT /calendars/{calendarId}"""
        return await self.request("PUT", f"/calendars/{calendar_id}",
                                  body=data)

    async def delete_calendar(self, calendar_id: str) -> dict:
        """DELETE /calendars/{calendarId}"""
        return await self.request("DELETE", f"/calendars/{calendar_id}")

    async def get_calendar_free_slots(self, calendar_id: str,
                                       start_date: str, end_date: str,
                                       timezone: str, **kwargs) -> dict:
        """GET /calendars/{calendarId}/free-slots
        Note: startDate/endDate must be epoch milliseconds (not date strings)."""
        # Convert date strings to epoch millis if needed
        import time
        from datetime import datetime as _dt
        def _to_epoch_ms(val):
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                try:
                    return int(val)
                except ValueError:
                    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
                        try:
                            return int(_dt.strptime(val.split("+")[0].split("Z")[0], fmt.split("+")[0].split("Z")[0]).timestamp() * 1000)
                        except ValueError:
                            continue
            return val
        return await self.request(
            "GET", f"/calendars/{calendar_id}/free-slots",
            query_params={"startDate": _to_epoch_ms(start_date),
                          "endDate": _to_epoch_ms(end_date),
                          "timezone": timezone, **kwargs})

    # --- Calendar Events / Appointments ---

    async def create_appointment(self, data: dict) -> dict:
        """POST /calendars/events/appointments"""
        return await self.request("POST", "/calendars/events/appointments",
                                  body=data)

    async def get_appointment(self, event_id: str) -> dict:
        """GET /calendars/events/appointments/{eventId}"""
        return await self.request(
            "GET", f"/calendars/events/appointments/{event_id}")

    async def update_appointment(self, event_id: str, data: dict) -> dict:
        """PUT /calendars/events/appointments/{eventId}"""
        return await self.request(
            "PUT", f"/calendars/events/appointments/{event_id}", body=data)

    async def get_calendar_events(self, **kwargs) -> dict:
        """GET /calendars/events
        Requires at least one of: calendarId, userId, groupId."""
        params = self._loc(kwargs)
        # Convert time strings to epoch millis if provided
        import time
        from datetime import datetime as _dt
        for key in ("startTime", "endTime"):
            if key in params and isinstance(params[key], str):
                try:
                    int(params[key])
                except ValueError:
                    try:
                        params[key] = str(int(_dt.fromisoformat(
                            params[key].replace("Z", "+00:00")).timestamp() * 1000))
                    except Exception:
                        pass
        return await self.request("GET", "/calendars/events",
                                  query_params=params)

    async def delete_calendar_event(self, event_id: str, data: dict) -> dict:
        """DELETE /calendars/events/{eventId}"""
        return await self.request("DELETE", f"/calendars/events/{event_id}",
                                  body=data)

    # --- Block Slots ---

    async def get_blocked_slots(self, **kwargs) -> dict:
        """GET /calendars/blocked-slots"""
        return await self.request("GET", "/calendars/blocked-slots",
                                  query_params=self._loc(kwargs))

    async def create_block_slot(self, data: dict) -> dict:
        """POST /calendars/events/block-slots"""
        return await self.request("POST", "/calendars/events/block-slots",
                                  body=data)

    async def update_block_slot(self, event_id: str, data: dict) -> dict:
        """PUT /calendars/events/block-slots/{eventId}"""
        return await self.request(
            "PUT", f"/calendars/events/block-slots/{event_id}", body=data)

    # --- Appointment Notes ---

    async def get_appointment_notes(self, appointment_id: str,
                                     **kwargs) -> dict:
        """GET /calendars/appointments/{appointmentId}/notes"""
        return await self.request(
            "GET", f"/calendars/appointments/{appointment_id}/notes",
            query_params=kwargs or None)

    async def create_appointment_note(self, appointment_id: str,
                                       data: dict) -> dict:
        """POST /calendars/appointments/{appointmentId}/notes"""
        return await self.request(
            "POST", f"/calendars/appointments/{appointment_id}/notes",
            body=data)

    async def update_appointment_note(self, appointment_id: str,
                                       note_id: str, data: dict) -> dict:
        """PUT /calendars/appointments/{appointmentId}/notes/{noteId}"""
        return await self.request(
            "PUT",
            f"/calendars/appointments/{appointment_id}/notes/{note_id}",
            body=data)

    async def delete_appointment_note(self, appointment_id: str,
                                       note_id: str) -> dict:
        """DELETE /calendars/appointments/{appointmentId}/notes/{noteId}"""
        return await self.request(
            "DELETE",
            f"/calendars/appointments/{appointment_id}/notes/{note_id}")

    # --- Calendar Resources ---

    async def get_calendar_resources(self, resource_type: str,
                                      **kwargs) -> dict:
        """GET /calendars/resources/{resourceType}"""
        return await self.request(
            "GET", f"/calendars/resources/{resource_type}",
            query_params=self._loc(kwargs))

    async def create_calendar_resource(self, resource_type: str,
                                        data: dict) -> dict:
        """POST /calendars/resources/{resourceType}"""
        return await self.request(
            "POST", f"/calendars/resources/{resource_type}", body=data)

    async def update_calendar_resource(self, resource_type: str,
                                        resource_id: str,
                                        data: dict) -> dict:
        """PUT /calendars/resources/{resourceType}/{id}"""
        return await self.request(
            "PUT", f"/calendars/resources/{resource_type}/{resource_id}",
            body=data)

    async def delete_calendar_resource(self, resource_type: str,
                                        resource_id: str) -> dict:
        """DELETE /calendars/resources/{resourceType}/{id}"""
        return await self.request(
            "DELETE", f"/calendars/resources/{resource_type}/{resource_id}")

    # --- Calendar Notifications ---

    async def get_calendar_notifications(self, calendar_id: str,
                                          **kwargs) -> dict:
        """GET /calendars/{calendarId}/notifications"""
        return await self.request(
            "GET", f"/calendars/{calendar_id}/notifications",
            query_params=kwargs or None)

    async def create_calendar_notifications(self, calendar_id: str,
                                             data: list) -> dict:
        """POST /calendars/{calendarId}/notifications"""
        return await self.request(
            "POST", f"/calendars/{calendar_id}/notifications", body=data)

    # =========================================================================
    # OPPORTUNITIES / PIPELINES
    # =========================================================================

    async def search_opportunities(self, **kwargs) -> dict:
        """GET /opportunities/search — uses location_id (underscore!)."""
        params = {"location_id": self.location_id, **kwargs}
        return await self.request("GET", "/opportunities/search",
                                  query_params=params)

    async def get_pipelines(self) -> dict:
        """GET /opportunities/pipelines"""
        return await self.request("GET", "/opportunities/pipelines",
                                  query_params=self._loc())

    async def get_opportunity(self, opportunity_id: str) -> dict:
        """GET /opportunities/{id}"""
        return await self.request("GET", f"/opportunities/{opportunity_id}")

    async def create_opportunity(self, data: dict) -> dict:
        """POST /opportunities/ - Required: pipelineId, name, status, contactId."""
        return await self.request("POST", "/opportunities/",
                                  body=self._loc_body(data))

    async def update_opportunity(self, opportunity_id: str,
                                  data: dict) -> dict:
        """PUT /opportunities/{id}"""
        return await self.request("PUT", f"/opportunities/{opportunity_id}",
                                  body=data)

    async def delete_opportunity(self, opportunity_id: str) -> dict:
        """DELETE /opportunities/{id}"""
        return await self.request("DELETE",
                                  f"/opportunities/{opportunity_id}")

    async def update_opportunity_status(self, opportunity_id: str,
                                         status: str) -> dict:
        """PUT /opportunities/{id}/status - status: open|won|lost|abandoned"""
        return await self.request(
            "PUT", f"/opportunities/{opportunity_id}/status",
            body={"status": status})

    async def upsert_opportunity(self, data: dict) -> dict:
        """POST /opportunities/upsert"""
        return await self.request("POST", "/opportunities/upsert",
                                  body=self._loc_body(data))

    async def add_opportunity_followers(self, opportunity_id: str,
                                         followers: list[str]) -> dict:
        """POST /opportunities/{id}/followers"""
        return await self.request(
            "POST", f"/opportunities/{opportunity_id}/followers",
            body={"followers": followers})

    async def remove_opportunity_followers(self, opportunity_id: str,
                                            followers: list[str]) -> dict:
        """DELETE /opportunities/{id}/followers"""
        return await self.request(
            "DELETE", f"/opportunities/{opportunity_id}/followers",
            body={"followers": followers})

    # =========================================================================
    # FUNNELS / WEBSITES
    # =========================================================================

    async def get_funnels(self, **kwargs) -> dict:
        """GET /funnels/funnel/list"""
        return await self.request("GET", "/funnels/funnel/list",
                                  query_params=self._loc(kwargs))

    async def get_funnel_pages(self, funnel_id: str, **kwargs) -> dict:
        """GET /funnels/page"""
        return await self.request("GET", "/funnels/page",
                                  query_params=self._loc(
                                      {"funnelId": funnel_id, **kwargs}))

    async def get_funnel_page_count(self, funnel_id: str, **kwargs) -> dict:
        """GET /funnels/page/count"""
        return await self.request("GET", "/funnels/page/count",
                                  query_params=self._loc(
                                      {"funnelId": funnel_id, **kwargs}))

    # --- Redirects ---

    async def get_redirects(self, **kwargs) -> dict:
        """GET /funnels/lookup/redirect/list"""
        return await self.request("GET", "/funnels/lookup/redirect/list",
                                  query_params=self._loc(kwargs))

    async def create_redirect(self, data: dict) -> dict:
        """POST /funnels/lookup/redirect"""
        return await self.request("POST", "/funnels/lookup/redirect",
                                  body=self._loc_body(data))

    async def update_redirect(self, redirect_id: str, data: dict) -> dict:
        """PATCH /funnels/lookup/redirect/{id}"""
        return await self.request(
            "PATCH", f"/funnels/lookup/redirect/{redirect_id}",
            body=self._loc_body(data))

    async def delete_redirect(self, redirect_id: str) -> dict:
        """DELETE /funnels/lookup/redirect/{id}"""
        return await self.request(
            "DELETE", f"/funnels/lookup/redirect/{redirect_id}",
            query_params=self._loc())

    # =========================================================================
    # FORMS
    # =========================================================================

    async def get_forms(self, **kwargs) -> dict:
        """GET /forms/"""
        return await self.request("GET", "/forms/",
                                  query_params=self._loc(kwargs))

    async def get_form_submissions(self, **kwargs) -> dict:
        """GET /forms/submissions — requires startAt, endAt date range."""
        params = self._loc(kwargs)
        if "startAt" not in params:
            params["startAt"] = "2024-01-01"
        if "endAt" not in params:
            params["endAt"] = "2027-12-31"
        if "page" not in params:
            params["page"] = 1
        if "limit" not in params:
            params["limit"] = 20
        return await self.request("GET", "/forms/submissions",
                                  query_params=params)

    async def upload_form_custom_files(self, contact_id: str,
                                        files: dict) -> dict:
        """POST /forms/upload-custom-files"""
        return await self.request(
            "POST", "/forms/upload-custom-files",
            query_params=self._loc({"contactId": contact_id}),
            files=files)

    # =========================================================================
    # SURVEYS
    # =========================================================================

    async def get_surveys(self, **kwargs) -> dict:
        """GET /surveys/"""
        return await self.request("GET", "/surveys/",
                                  query_params=self._loc(kwargs))

    async def get_survey_submissions(self, **kwargs) -> dict:
        """GET /surveys/submissions"""
        return await self.request("GET", "/surveys/submissions",
                                  query_params=self._loc(kwargs))

    # =========================================================================
    # WORKFLOWS
    # =========================================================================

    async def get_workflows(self) -> dict:
        """GET /workflows/"""
        return await self.request("GET", "/workflows/",
                                  query_params=self._loc())

    # =========================================================================
    # CUSTOM FIELDS V2
    # =========================================================================

    async def get_custom_field(self, field_id: str) -> dict:
        """GET /custom-fields/{id}"""
        return await self.request("GET", f"/custom-fields/{field_id}")

    async def create_custom_field_v2(self, data: dict) -> dict:
        """POST /custom-fields/ - dataType: TEXT, LARGE_TEXT, NUMERICAL, PHONE,
        MONETORY, CHECKBOX, SINGLE_OPTIONS, MULTIPLE_OPTIONS, DATE,
        TEXTBOX_LIST, FILE_UPLOAD, RADIO, EMAIL."""
        return await self.request("POST", "/custom-fields/",
                                  body=self._loc_body(data))

    async def update_custom_field_v2(self, field_id: str, data: dict) -> dict:
        """PUT /custom-fields/{id}"""
        return await self.request("PUT", f"/custom-fields/{field_id}",
                                  body=self._loc_body(data))

    async def delete_custom_field_v2(self, field_id: str) -> dict:
        """DELETE /custom-fields/{id}"""
        return await self.request("DELETE", f"/custom-fields/{field_id}")

    async def get_custom_fields_by_object(self, object_key: str) -> dict:
        """GET /custom-fields/object-key/{objectKey}"""
        return await self.request(
            "GET", f"/custom-fields/object-key/{object_key}",
            query_params=self._loc())

    async def create_custom_field_folder(self, name: str,
                                          object_key: str) -> dict:
        """POST /custom-fields/folder"""
        return await self.request("POST", "/custom-fields/folder",
                                  body=self._loc_body({"name": name,
                                                       "objectKey": object_key}))

    async def update_custom_field_folder(self, folder_id: str,
                                          name: str) -> dict:
        """PUT /custom-fields/folder/{id}"""
        return await self.request("PUT", f"/custom-fields/folder/{folder_id}",
                                  body=self._loc_body({"name": name}))

    async def delete_custom_field_folder(self, folder_id: str) -> dict:
        """DELETE /custom-fields/folder/{id}"""
        return await self.request("DELETE",
                                  f"/custom-fields/folder/{folder_id}",
                                  query_params=self._loc())

    # =========================================================================
    # LOCATIONS / SUB-ACCOUNTS
    # =========================================================================

    async def search_locations(self, company_id: str, **kwargs) -> dict:
        """GET /locations/search"""
        return await self.request("GET", "/locations/search",
                                  query_params={"companyId": company_id,
                                                **kwargs})

    async def get_location(self, location_id: str | None = None) -> dict:
        """GET /locations/{locationId}"""
        loc = location_id or self.location_id
        return await self.request("GET", f"/locations/{loc}")

    async def update_location(self, location_id: str, data: dict) -> dict:
        """PUT /locations/{locationId}"""
        return await self.request("PUT", f"/locations/{location_id}",
                                  body=data)

    async def delete_location(self, location_id: str,
                               delete_twilio: bool = False) -> dict:
        """DELETE /locations/{locationId}"""
        return await self.request(
            "DELETE", f"/locations/{location_id}",
            query_params={"deleteTwilioAccount": delete_twilio})

    # --- Location Tags ---

    async def get_tags(self, location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/tags"""
        loc = location_id or self.location_id
        return await self.request("GET", f"/locations/{loc}/tags")

    async def create_tag(self, name: str,
                          location_id: str | None = None) -> dict:
        """POST /locations/{locationId}/tags"""
        loc = location_id or self.location_id
        return await self.request("POST", f"/locations/{loc}/tags",
                                  body={"name": name})

    async def update_tag(self, tag_id: str, name: str,
                          location_id: str | None = None) -> dict:
        """PUT /locations/{locationId}/tags/{tagId}"""
        loc = location_id or self.location_id
        return await self.request("PUT", f"/locations/{loc}/tags/{tag_id}",
                                  body={"name": name})

    async def delete_tag(self, tag_id: str,
                          location_id: str | None = None) -> dict:
        """DELETE /locations/{locationId}/tags/{tagId}"""
        loc = location_id or self.location_id
        return await self.request("DELETE", f"/locations/{loc}/tags/{tag_id}")

    # --- Location Tasks ---

    async def search_tasks(self, data: dict,
                            location_id: str | None = None) -> dict:
        """POST /locations/{locationId}/tasks/search"""
        loc = location_id or self.location_id
        return await self.request("POST", f"/locations/{loc}/tasks/search",
                                  body=data)

    # --- Location Custom Fields (legacy v1 path) ---

    async def get_custom_fields(self, model: str = "all",
                                 location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/customFields"""
        loc = location_id or self.location_id
        return await self.request("GET", f"/locations/{loc}/customFields",
                                  query_params={"model": model})

    async def create_custom_field(self, name: str, data_type: str,
                                   **kwargs) -> dict:
        """POST /locations/{locationId}/customFields"""
        loc = kwargs.pop("location_id", None) or self.location_id
        return await self.request("POST", f"/locations/{loc}/customFields",
                                  body={"name": name, "dataType": data_type,
                                        **kwargs})

    async def update_custom_field(self, field_id: str, name: str,
                                   location_id: str | None = None,
                                   **kwargs) -> dict:
        """PUT /locations/{locationId}/customFields/{fieldId}"""
        loc = location_id or self.location_id
        return await self.request(
            "PUT", f"/locations/{loc}/customFields/{field_id}",
            body={"name": name, **kwargs})

    async def delete_custom_field(self, field_id: str,
                                   location_id: str | None = None) -> dict:
        """DELETE /locations/{locationId}/customFields/{fieldId}"""
        loc = location_id or self.location_id
        return await self.request(
            "DELETE", f"/locations/{loc}/customFields/{field_id}")

    # --- Location Custom Values ---

    async def get_custom_values(self,
                                 location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/customValues"""
        loc = location_id or self.location_id
        return await self.request("GET", f"/locations/{loc}/customValues")

    async def create_custom_value(self, name: str, value: str,
                                   location_id: str | None = None) -> dict:
        """POST /locations/{locationId}/customValues"""
        loc = location_id or self.location_id
        return await self.request("POST", f"/locations/{loc}/customValues",
                                  body={"name": name, "value": value})

    async def update_custom_value(self, value_id: str, name: str,
                                   value: str,
                                   location_id: str | None = None) -> dict:
        """PUT /locations/{locationId}/customValues/{id}"""
        loc = location_id or self.location_id
        return await self.request(
            "PUT", f"/locations/{loc}/customValues/{value_id}",
            body={"name": name, "value": value})

    async def delete_custom_value(self, value_id: str,
                                   location_id: str | None = None) -> dict:
        """DELETE /locations/{locationId}/customValues/{id}"""
        loc = location_id or self.location_id
        return await self.request(
            "DELETE", f"/locations/{loc}/customValues/{value_id}")

    # --- Location Templates (SMS / Email) ---

    async def get_templates(self, location_id: str | None = None,
                             **kwargs) -> dict:
        """GET /locations/{locationId}/templates"""
        loc = location_id or self.location_id
        return await self.request("GET", f"/locations/{loc}/templates",
                                  query_params=kwargs or None)

    async def create_template(self, data: dict,
                               location_id: str | None = None) -> dict:
        """POST /locations/{locationId}/templates"""
        loc = location_id or self.location_id
        return await self.request("POST", f"/locations/{loc}/templates",
                                  body=data)

    async def get_template(self, template_id: str,
                            location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/templates/{templateId}"""
        loc = location_id or self.location_id
        return await self.request(
            "GET", f"/locations/{loc}/templates/{template_id}")

    async def update_template(self, template_id: str, data: dict,
                               location_id: str | None = None) -> dict:
        """PUT /locations/{locationId}/templates/{templateId}"""
        loc = location_id or self.location_id
        return await self.request(
            "PUT", f"/locations/{loc}/templates/{template_id}", body=data)

    async def delete_template(self, template_id: str,
                               location_id: str | None = None) -> dict:
        """DELETE /locations/{locationId}/templates/{templateId}"""
        loc = location_id or self.location_id
        return await self.request(
            "DELETE", f"/locations/{loc}/templates/{template_id}")

    # =========================================================================
    # EMAILS (Campaigns / Builder)
    # =========================================================================

    async def get_email_campaigns(self, **kwargs) -> dict:
        """GET /emails/schedule"""
        return await self.request("GET", "/emails/schedule",
                                  query_params=self._loc(kwargs))

    async def create_email_template(self, data: dict) -> dict:
        """POST /emails/builder"""
        return await self.request("POST", "/emails/builder",
                                  body=self._loc_body(data))

    async def get_email_templates(self, **kwargs) -> dict:
        """GET /emails/builder"""
        return await self.request("GET", "/emails/builder",
                                  query_params=self._loc(kwargs))

    async def delete_email_template(self, template_id: str) -> dict:
        """DELETE /emails/builder/{locationId}/{templateId}"""
        return await self.request(
            "DELETE", f"/emails/builder/{self.location_id}/{template_id}")

    async def update_email_template_data(self, data: dict) -> dict:
        """POST /emails/builder/data - Update template HTML/builder content."""
        return await self.request("POST", "/emails/builder/data",
                                  body=self._loc_body(data))

    # =========================================================================
    # PRODUCTS
    # =========================================================================

    async def get_products(self, **kwargs) -> dict:
        """GET /products/"""
        return await self.request("GET", "/products/",
                                  query_params=self._loc(kwargs))

    async def create_product(self, data: dict) -> dict:
        """POST /products/"""
        return await self.request("POST", "/products/",
                                  body=self._loc_body(data))

    async def get_product(self, product_id: str) -> dict:
        """GET /products/{productId}"""
        return await self.request("GET", f"/products/{product_id}",
                                  query_params=self._loc())

    async def update_product(self, product_id: str, data: dict) -> dict:
        """PUT /products/{productId}"""
        return await self.request("PUT", f"/products/{product_id}", body=data)

    async def delete_product(self, product_id: str) -> dict:
        """DELETE /products/{productId}"""
        return await self.request("DELETE", f"/products/{product_id}",
                                  query_params=self._loc())

    async def bulk_update_products(self, data: dict) -> dict:
        """POST /products/bulk-update"""
        return await self.request("POST", "/products/bulk-update", body=data)

    # --- Product Prices ---

    async def create_product_price(self, product_id: str,
                                    data: dict) -> dict:
        """POST /products/{productId}/price"""
        return await self.request("POST", f"/products/{product_id}/price",
                                  body=data)

    async def get_product_prices(self, product_id: str, **kwargs) -> dict:
        """GET /products/{productId}/price"""
        return await self.request("GET", f"/products/{product_id}/price",
                                  query_params=self._loc(kwargs))

    async def update_product_price(self, product_id: str, price_id: str,
                                    data: dict) -> dict:
        """PUT /products/{productId}/price/{priceId}"""
        return await self.request(
            "PUT", f"/products/{product_id}/price/{price_id}", body=data)

    async def delete_product_price(self, product_id: str,
                                    price_id: str) -> dict:
        """DELETE /products/{productId}/price/{priceId}"""
        return await self.request(
            "DELETE", f"/products/{product_id}/price/{price_id}",
            query_params=self._loc())

    # --- Product Inventory ---

    async def get_inventory(self, **kwargs) -> dict:
        """GET /products/inventory"""
        return await self.request("GET", "/products/inventory",
                                  query_params=kwargs)

    async def update_inventory(self, data: dict) -> dict:
        """POST /products/inventory"""
        return await self.request("POST", "/products/inventory", body=data)

    # --- Product Collections ---

    async def get_collections(self, **kwargs) -> dict:
        """GET /products/collections"""
        return await self.request("GET", "/products/collections",
                                  query_params=kwargs)

    async def create_collection(self, data: dict) -> dict:
        """POST /products/collections"""
        return await self.request("POST", "/products/collections", body=data)

    async def update_collection(self, collection_id: str,
                                 data: dict) -> dict:
        """PUT /products/collections/{collectionId}"""
        return await self.request(
            "PUT", f"/products/collections/{collection_id}", body=data)

    async def delete_collection(self, collection_id: str) -> dict:
        """DELETE /products/collections/{collectionId}"""
        return await self.request(
            "DELETE", f"/products/collections/{collection_id}")

    # --- Product Reviews ---

    async def get_product_reviews(self, **kwargs) -> dict:
        """GET /products/reviews"""
        return await self.request("GET", "/products/reviews",
                                  query_params=kwargs)

    async def update_product_review(self, review_id: str,
                                     data: dict) -> dict:
        """PUT /products/reviews/{reviewId}"""
        return await self.request("PUT", f"/products/reviews/{review_id}",
                                  body=data)

    async def delete_product_review(self, review_id: str) -> dict:
        """DELETE /products/reviews/{reviewId}"""
        return await self.request("DELETE", f"/products/reviews/{review_id}")

    # =========================================================================
    # PAYMENTS
    # =========================================================================

    async def get_orders(self, **kwargs) -> dict:
        """GET /payments/orders"""
        return await self.request("GET", "/payments/orders",
                                  query_params=self._loc(kwargs))

    async def get_order(self, order_id: str) -> dict:
        """GET /payments/orders/{orderId}"""
        return await self.request("GET", f"/payments/orders/{order_id}",
                                  query_params=self._loc())

    async def record_order_payment(self, order_id: str, data: dict) -> dict:
        """POST /payments/orders/{orderId}/record-payment"""
        return await self.request(
            "POST", f"/payments/orders/{order_id}/record-payment", body=data)

    async def get_transactions(self, **kwargs) -> dict:
        """GET /payments/transactions"""
        return await self.request("GET", "/payments/transactions",
                                  query_params=self._loc(kwargs))

    async def get_transaction(self, transaction_id: str) -> dict:
        """GET /payments/transactions/{transactionId}"""
        return await self.request(
            "GET", f"/payments/transactions/{transaction_id}",
            query_params=self._loc())

    async def get_subscriptions(self, **kwargs) -> dict:
        """GET /payments/subscriptions"""
        return await self.request("GET", "/payments/subscriptions",
                                  query_params=kwargs)

    async def get_subscription(self, subscription_id: str) -> dict:
        """GET /payments/subscriptions/{subscriptionId}"""
        return await self.request(
            "GET", f"/payments/subscriptions/{subscription_id}")

    # --- Coupons ---

    async def get_coupons(self, **kwargs) -> dict:
        """GET /payments/coupon/list"""
        params = {"altId": self.location_id, "altType": "location", **kwargs}
        return await self.request("GET", "/payments/coupon/list",
                                  query_params=params)

    async def create_coupon(self, data: dict) -> dict:
        """POST /payments/coupon"""
        return await self.request("POST", "/payments/coupon", body=data)

    async def update_coupon(self, data: dict) -> dict:
        """PUT /payments/coupon"""
        return await self.request("PUT", "/payments/coupon", body=data)

    async def delete_coupon(self, data: dict) -> dict:
        """DELETE /payments/coupon"""
        return await self.request("DELETE", "/payments/coupon", body=data)

    # =========================================================================
    # INVOICES
    # =========================================================================

    async def get_invoice(self, invoice_id: str, **kwargs) -> dict:
        """GET /invoices/{invoiceId}"""
        return await self.request("GET", f"/invoices/{invoice_id}",
                                  query_params=kwargs)

    async def update_invoice(self, invoice_id: str, data: dict) -> dict:
        """PUT /invoices/{invoiceId}"""
        return await self.request("PUT", f"/invoices/{invoice_id}", body=data)

    async def delete_invoice(self, invoice_id: str, **kwargs) -> dict:
        """DELETE /invoices/{invoiceId}"""
        return await self.request("DELETE", f"/invoices/{invoice_id}",
                                  query_params=kwargs)

    async def void_invoice(self, invoice_id: str, data: dict) -> dict:
        """POST /invoices/{invoiceId}/void"""
        return await self.request("POST", f"/invoices/{invoice_id}/void",
                                  body=data)

    async def send_invoice(self, invoice_id: str, data: dict) -> dict:
        """POST /invoices/{invoiceId}/send"""
        return await self.request("POST", f"/invoices/{invoice_id}/send",
                                  body=data)

    async def record_invoice_payment(self, invoice_id: str,
                                      data: dict) -> dict:
        """POST /invoices/{invoiceId}/record-payment"""
        return await self.request(
            "POST", f"/invoices/{invoice_id}/record-payment", body=data)

    async def generate_invoice_number(self, **kwargs) -> dict:
        """GET /invoices/generate-invoice-number"""
        return await self.request("GET", "/invoices/generate-invoice-number",
                                  query_params=kwargs)

    # --- Invoice Templates ---

    async def create_invoice_template(self, data: dict) -> dict:
        """POST /invoices/template"""
        return await self.request("POST", "/invoices/template", body=data)

    async def get_invoice_templates(self, **kwargs) -> dict:
        """GET /invoices/template"""
        return await self.request("GET", "/invoices/template",
                                  query_params=kwargs)

    async def update_invoice_template(self, template_id: str,
                                       data: dict) -> dict:
        """PUT /invoices/template/{templateId}"""
        return await self.request(
            "PUT", f"/invoices/template/{template_id}", body=data)

    async def delete_invoice_template(self, template_id: str,
                                       **kwargs) -> dict:
        """DELETE /invoices/template/{templateId}"""
        return await self.request(
            "DELETE", f"/invoices/template/{template_id}",
            query_params=kwargs)

    # --- Invoice Schedules ---

    async def create_invoice_schedule(self, data: dict) -> dict:
        """POST /invoices/schedule"""
        return await self.request("POST", "/invoices/schedule", body=data)

    async def get_invoice_schedules(self, **kwargs) -> dict:
        """GET /invoices/schedule"""
        return await self.request("GET", "/invoices/schedule",
                                  query_params=kwargs)

    async def schedule_invoice(self, schedule_id: str, data: dict) -> dict:
        """POST /invoices/schedule/{scheduleId}/schedule"""
        return await self.request(
            "POST", f"/invoices/schedule/{schedule_id}/schedule", body=data)

    async def cancel_invoice_schedule(self, schedule_id: str,
                                       data: dict) -> dict:
        """POST /invoices/schedule/{scheduleId}/cancel"""
        return await self.request(
            "POST", f"/invoices/schedule/{schedule_id}/cancel", body=data)

    # --- Estimates ---

    async def create_estimate(self, data: dict) -> dict:
        """POST /invoices/estimate"""
        return await self.request("POST", "/invoices/estimate", body=data)

    async def get_estimates(self, **kwargs) -> dict:
        """GET /invoices/estimate/list"""
        return await self.request("GET", "/invoices/estimate/list",
                                  query_params=kwargs)

    async def send_estimate(self, estimate_id: str, data: dict) -> dict:
        """POST /invoices/estimate/{estimateId}/send"""
        return await self.request(
            "POST", f"/invoices/estimate/{estimate_id}/send", body=data)

    async def convert_estimate_to_invoice(self, estimate_id: str,
                                           data: dict) -> dict:
        """POST /invoices/estimate/{estimateId}/invoice"""
        return await self.request(
            "POST", f"/invoices/estimate/{estimate_id}/invoice", body=data)

    # =========================================================================
    # CAMPAIGNS
    # =========================================================================

    async def get_campaigns(self, **kwargs) -> dict:
        """GET /campaigns/"""
        return await self.request("GET", "/campaigns/",
                                  query_params=self._loc(kwargs))

    # =========================================================================
    # BLOGS
    # =========================================================================

    async def get_blogs(self, **kwargs) -> dict:
        """GET /blogs/site/all"""
        return await self.request("GET", "/blogs/site/all",
                                  query_params=self._loc(kwargs))

    async def get_blog_posts(self, blog_id: str, **kwargs) -> dict:
        """GET /blogs/posts/all"""
        return await self.request("GET", "/blogs/posts/all",
                                  query_params=self._loc(
                                      {"blogId": blog_id, **kwargs}))

    async def create_blog_post(self, data: dict) -> dict:
        """POST /blogs/posts"""
        return await self.request("POST", "/blogs/posts",
                                  body=self._loc_body(data))

    async def update_blog_post(self, post_id: str, data: dict) -> dict:
        """PUT /blogs/posts/{postId}"""
        return await self.request("PUT", f"/blogs/posts/{post_id}",
                                  body=self._loc_body(data))

    async def check_blog_url_slug(self, url_slug: str) -> dict:
        """GET /blogs/posts/url-slug-exists"""
        return await self.request("GET", "/blogs/posts/url-slug-exists",
                                  query_params=self._loc(
                                      {"urlSlug": url_slug}))

    async def get_blog_authors(self, **kwargs) -> dict:
        """GET /blogs/authors"""
        return await self.request("GET", "/blogs/authors",
                                  query_params=self._loc(kwargs))

    async def get_blog_categories(self, **kwargs) -> dict:
        """GET /blogs/categories"""
        return await self.request("GET", "/blogs/categories",
                                  query_params=self._loc(kwargs))

    # =========================================================================
    # COURSES
    # =========================================================================

    async def import_courses(self, data: dict) -> dict:
        """POST /courses/courses-exporter/public/import"""
        return await self.request(
            "POST", "/courses/courses-exporter/public/import",
            body=self._loc_body(data))

    # =========================================================================
    # MEDIA LIBRARY
    # =========================================================================

    async def get_media_files(self, **kwargs) -> dict:
        """GET /medias/files — requires type param: file, folder, all."""
        params = {"altType": "location", "altId": self.location_id,
                  "sortBy": "createdAt", "sortOrder": "desc", **kwargs}
        if "type" not in params:
            params["type"] = "file"
        return await self.request("GET", "/medias/files",
                                  query_params=params)

    async def upload_media_file(self, file_data: dict) -> dict:
        """POST /medias/upload-file (multipart)"""
        return await self.request("POST", "/medias/upload-file",
                                  files=file_data)

    async def update_media_file(self, file_id: str, name: str) -> dict:
        """POST /medias/{id}"""
        return await self.request("POST", f"/medias/{file_id}",
                                  body={"name": name, "altType": "location",
                                        "altId": self.location_id})

    async def delete_media_file(self, file_id: str) -> dict:
        """DELETE /medias/{id}"""
        return await self.request("DELETE", f"/medias/{file_id}",
                                  query_params={"altType": "location",
                                                "altId": self.location_id})

    async def create_media_folder(self, name: str,
                                   parent_id: str | None = None) -> dict:
        """POST /medias/folder"""
        body: dict[str, Any] = {"name": name, "altType": "location",
                                "altId": self.location_id}
        if parent_id:
            body["parentId"] = parent_id
        return await self.request("POST", "/medias/folder", body=body)

    async def bulk_delete_media(self, file_ids: list[str],
                                 status: str = "deleted") -> dict:
        """PUT /medias/delete-files"""
        return await self.request("PUT", "/medias/delete-files", body={
            "filesToBeDeleted": [{"_id": fid} for fid in file_ids],
            "altType": "location", "altId": self.location_id,
            "status": status,
        })

    # =========================================================================
    # USERS
    # =========================================================================

    async def search_users(self, company_id: str, **kwargs) -> dict:
        """GET /users/search"""
        return await self.request("GET", "/users/search",
                                  query_params={"companyId": company_id,
                                                **kwargs})

    async def get_user(self, user_id: str) -> dict:
        """GET /users/{userId}"""
        return await self.request("GET", f"/users/{user_id}")

    async def create_user(self, data: dict) -> dict:
        """POST /users/"""
        return await self.request("POST", "/users/", body=data)

    async def update_user(self, user_id: str, data: dict) -> dict:
        """PUT /users/{userId}"""
        return await self.request("PUT", f"/users/{user_id}", body=data)

    async def delete_user(self, user_id: str) -> dict:
        """DELETE /users/{userId}"""
        return await self.request("DELETE", f"/users/{user_id}")

    async def get_users_by_location(self) -> dict:
        """GET /users/"""
        return await self.request("GET", "/users/",
                                  query_params=self._loc())

    # =========================================================================
    # SOCIAL MEDIA POSTING
    # =========================================================================

    async def create_social_post(self, data: dict) -> dict:
        """POST /social-media-posting/{locationId}/posts"""
        return await self.request(
            "POST", f"/social-media-posting/{self.location_id}/posts",
            body=data)

    async def get_social_post(self, post_id: str) -> dict:
        """GET /social-media-posting/{locationId}/posts/{id}"""
        return await self.request(
            "GET",
            f"/social-media-posting/{self.location_id}/posts/{post_id}")

    async def update_social_post(self, post_id: str, data: dict) -> dict:
        """PUT /social-media-posting/{locationId}/posts/{id}"""
        return await self.request(
            "PUT",
            f"/social-media-posting/{self.location_id}/posts/{post_id}",
            body=data)

    async def delete_social_post(self, post_id: str) -> dict:
        """DELETE /social-media-posting/{locationId}/posts/{id}"""
        return await self.request(
            "DELETE",
            f"/social-media-posting/{self.location_id}/posts/{post_id}")

    async def search_social_posts(self, data: dict) -> dict:
        """POST /social-media-posting/{locationId}/posts/list"""
        return await self.request(
            "POST",
            f"/social-media-posting/{self.location_id}/posts/list",
            body=data)

    async def get_social_accounts(self) -> dict:
        """GET /social-media-posting/{locationId}/accounts"""
        return await self.request(
            "GET", f"/social-media-posting/{self.location_id}/accounts")

    async def delete_social_account(self, account_id: str) -> dict:
        """DELETE /social-media-posting/{locationId}/accounts/{id}"""
        return await self.request(
            "DELETE",
            f"/social-media-posting/{self.location_id}/accounts/{account_id}")

    # =========================================================================
    # TRIGGER LINKS
    # =========================================================================

    async def get_links(self) -> dict:
        """GET /links/"""
        return await self.request("GET", "/links/",
                                  query_params=self._loc())

    async def create_link(self, name: str, redirect_to: str) -> dict:
        """POST /links/"""
        return await self.request("POST", "/links/",
                                  body=self._loc_body({"name": name,
                                                       "redirectTo": redirect_to}))

    async def get_link(self, link_id: str) -> dict:
        """GET /links/id/{linkId}"""
        return await self.request("GET", f"/links/id/{link_id}",
                                  query_params=self._loc())

    async def update_link(self, link_id: str, name: str,
                           redirect_to: str) -> dict:
        """PUT /links/{linkId}"""
        return await self.request("PUT", f"/links/{link_id}",
                                  body={"name": name,
                                        "redirectTo": redirect_to})

    async def delete_link(self, link_id: str) -> dict:
        """DELETE /links/{linkId}"""
        return await self.request("DELETE", f"/links/{link_id}")

    async def search_links(self, **kwargs) -> dict:
        """GET /links/search"""
        return await self.request("GET", "/links/search",
                                  query_params=self._loc(kwargs))

    # =========================================================================
    # BUSINESSES
    # =========================================================================

    async def get_businesses(self) -> dict:
        """GET /businesses/"""
        return await self.request("GET", "/businesses/",
                                  query_params=self._loc())

    async def create_business(self, data: dict) -> dict:
        """POST /businesses/"""
        return await self.request("POST", "/businesses/",
                                  body=self._loc_body(data))

    async def get_business(self, business_id: str) -> dict:
        """GET /businesses/{businessId}"""
        return await self.request("GET", f"/businesses/{business_id}")

    async def update_business(self, business_id: str, data: dict) -> dict:
        """PUT /businesses/{businessId}"""
        return await self.request("PUT", f"/businesses/{business_id}",
                                  body=data)

    async def delete_business(self, business_id: str) -> dict:
        """DELETE /businesses/{businessId}"""
        return await self.request("DELETE", f"/businesses/{business_id}",
                                  query_params=self._loc())

    # =========================================================================
    # COMPANIES
    # =========================================================================

    async def get_company(self, company_id: str) -> dict:
        """GET /companies/{companyId}"""
        return await self.request("GET", f"/companies/{company_id}")

    # =========================================================================
    # SNAPSHOTS
    # =========================================================================

    async def get_snapshots(self, company_id: str) -> dict:
        """GET /snapshots/"""
        return await self.request("GET", "/snapshots/",
                                  query_params={"companyId": company_id})

    async def create_snapshot_share_link(self, company_id: str,
                                          data: dict) -> dict:
        """POST /snapshots/share/link"""
        return await self.request("POST", "/snapshots/share/link",
                                  query_params={"companyId": company_id},
                                  body=data)

    async def get_snapshot_push_status(self, snapshot_id: str,
                                        company_id: str, **kwargs) -> dict:
        """GET /snapshots/snapshot-status/{snapshotId}"""
        return await self.request(
            "GET", f"/snapshots/snapshot-status/{snapshot_id}",
            query_params={"companyId": company_id, **kwargs})

    # =========================================================================
    # ASSOCIATIONS / RELATIONS
    # =========================================================================

    async def get_associations(self, **kwargs) -> dict:
        """GET /associations/"""
        return await self.request("GET", "/associations/",
                                  query_params=self._loc(kwargs))

    async def create_association(self, data: dict) -> dict:
        """POST /associations/"""
        return await self.request("POST", "/associations/",
                                  body=self._loc_body(data))

    async def get_association(self, association_id: str) -> dict:
        """GET /associations/{associationId}"""
        return await self.request("GET",
                                  f"/associations/{association_id}")

    async def update_association(self, association_id: str,
                                  data: dict) -> dict:
        """PUT /associations/{associationId}"""
        return await self.request("PUT",
                                  f"/associations/{association_id}",
                                  body=data)

    async def delete_association(self, association_id: str) -> dict:
        """DELETE /associations/{associationId}"""
        return await self.request("DELETE",
                                  f"/associations/{association_id}")

    async def create_relation(self, data: dict) -> dict:
        """POST /associations/relations"""
        return await self.request("POST", "/associations/relations",
                                  body=self._loc_body(data))

    async def get_relations(self, record_id: str, **kwargs) -> dict:
        """GET /associations/relations/{recordId}"""
        return await self.request(
            "GET", f"/associations/relations/{record_id}",
            query_params=self._loc(kwargs))

    async def delete_relation(self, relation_id: str) -> dict:
        """DELETE /associations/relations/{relationId}"""
        return await self.request(
            "DELETE", f"/associations/relations/{relation_id}",
            query_params=self._loc())

    # =========================================================================
    # CONVERSATION AI (Agents / Bots)
    # =========================================================================

    async def create_ai_agent(self, data: dict) -> dict:
        """POST /conversation-ai/agents - Create a Conversation AI agent.

        Required fields: name, personality (string), goal (string), instructions (string)
        Optional: mode (autopilot/suggestive/off), isPrimary, autoPilotMaxMessages,
                  sleepEnabled, sleepTime, sleepTimeUnit
        Note: locationId goes in query params, NOT body.
        """
        return await self.request("POST", "/conversation-ai/agents",
                                  body=data, query_params=self._loc())

    async def get_ai_agents(self, **kwargs) -> dict:
        """GET /conversation-ai/agents/search - List/search agents.
        No locationId needed — determined by API key."""
        return await self.request("GET", "/conversation-ai/agents/search",
                                  query_params=kwargs or None)

    async def get_ai_agent(self, agent_id: str) -> dict:
        """GET /conversation-ai/agents/{agentId} - Get agent full config.
        No locationId needed — determined by API key."""
        return await self.request("GET",
                                  f"/conversation-ai/agents/{agent_id}")

    async def update_ai_agent(self, agent_id: str, data: dict) -> dict:
        """PUT /conversation-ai/agents/{agentId} - Update agent.
        Note: Requires personality, goal, and instructions fields."""
        return await self.request("PUT",
                                  f"/conversation-ai/agents/{agent_id}",
                                  body=data, query_params=self._loc())

    async def delete_ai_agent(self, agent_id: str) -> dict:
        """DELETE /conversation-ai/agents/{agentId} - Delete agent."""
        return await self.request("DELETE",
                                  f"/conversation-ai/agents/{agent_id}")

    # --- Agent Actions ---

    async def create_ai_agent_action(self, agent_id: str,
                                      data: dict) -> dict:
        """POST /conversation-ai/agents/{agentId}/actions
        Attach an action to an agent.

        Action types: appointmentBooking, contactCollection,
                      transfer, workflow, followUp, stopBot,
                      CUSTOM_ACTION, KNOWLEDGE_BASE
        """
        return await self.request(
            "POST", f"/conversation-ai/agents/{agent_id}/actions",
            body=data)

    async def get_ai_agent_actions(self, agent_id: str) -> dict:
        """GET /conversation-ai/agents/{agentId}/actions"""
        return await self.request(
            "GET", f"/conversation-ai/agents/{agent_id}/actions")

    async def get_ai_agent_action(self, agent_id: str,
                                    action_id: str) -> dict:
        """GET /conversation-ai/agents/{agentId}/actions/{actionId}"""
        return await self.request(
            "GET",
            f"/conversation-ai/agents/{agent_id}/actions/{action_id}")

    async def update_ai_agent_action(self, agent_id: str,
                                       action_id: str,
                                       data: dict) -> dict:
        """PATCH /conversation-ai/agents/{agentId}/actions/{actionId}"""
        return await self.request(
            "PATCH",
            f"/conversation-ai/agents/{agent_id}/actions/{action_id}",
            body=data)

    async def delete_ai_agent_action(self, agent_id: str,
                                       action_id: str) -> dict:
        """DELETE /conversation-ai/agents/{agentId}/actions/{actionId}"""
        return await self.request(
            "DELETE",
            f"/conversation-ai/agents/{agent_id}/actions/{action_id}")

    # --- AI Generations (Debug/Audit) ---

    async def get_ai_generations(self, **kwargs) -> dict:
        """GET /conversation-ai/generations
        Get AI response generation details (system prompt, context, etc.)
        """
        return await self.request("GET", "/conversation-ai/generations",
                                  query_params=self._loc(kwargs))

    # =========================================================================
    # PAYMENTS - Extended (Fulfillments, Order Notes, Whitelabel, Custom Provider)
    # =========================================================================

    async def create_order_fulfillment(self, order_id: str, data: dict) -> dict:
        """POST /payments/orders/{orderId}/fulfillments"""
        return await self.request("POST",
                                  f"/payments/orders/{order_id}/fulfillments",
                                  body=data)

    async def get_order_fulfillments(self, order_id: str) -> dict:
        """GET /payments/orders/{orderId}/fulfillments"""
        return await self.request("GET",
                                  f"/payments/orders/{order_id}/fulfillments")

    async def get_order_notes(self, order_id: str) -> dict:
        """GET /payments/orders/{orderId}/notes"""
        return await self.request("GET",
                                  f"/payments/orders/{order_id}/notes")

    async def get_coupon(self, **kwargs) -> dict:
        """GET /payments/coupon - Fetch a specific coupon."""
        return await self.request("GET", "/payments/coupon",
                                  query_params=kwargs)

    # --- Whitelabel Integration ---

    async def create_whitelabel_integration(self, data: dict) -> dict:
        """POST /payments/integrations/provider/whitelabel"""
        return await self.request("POST",
                                  "/payments/integrations/provider/whitelabel",
                                  body=data)

    async def get_whitelabel_integrations(self) -> dict:
        """GET /payments/integrations/provider/whitelabel"""
        return await self.request("GET",
                                  "/payments/integrations/provider/whitelabel")

    # --- Custom Provider Extended ---

    async def get_custom_provider_config(self, **kwargs) -> dict:
        """GET /payments/custom-provider/connect"""
        return await self.request("GET", "/payments/custom-provider/connect",
                                  query_params=kwargs)

    async def create_custom_provider_config(self, data: dict) -> dict:
        """POST /payments/custom-provider/connect"""
        return await self.request("POST", "/payments/custom-provider/connect",
                                  body=data)

    async def disconnect_custom_provider(self, data: dict) -> dict:
        """POST /payments/custom-provider/disconnect"""
        return await self.request("POST",
                                  "/payments/custom-provider/disconnect",
                                  body=data)

    async def update_custom_provider_capabilities(self, data: dict) -> dict:
        """PUT /payments/custom-provider/capabilities"""
        return await self.request("PUT",
                                  "/payments/custom-provider/capabilities",
                                  body=data)

    async def create_custom_provider(self, data: dict) -> dict:
        """POST /payments/custom-provider/provider"""
        return await self.request("POST",
                                  "/payments/custom-provider/provider",
                                  body=data)

    async def delete_custom_provider(self, data: dict) -> dict:
        """DELETE /payments/custom-provider/provider"""
        return await self.request("DELETE",
                                  "/payments/custom-provider/provider",
                                  body=data)

    # =========================================================================
    # INVOICES - Extended (Text2Pay, Late Fees, Estimates Extended)
    # =========================================================================

    async def create_invoice(self, data: dict) -> dict:
        """POST /invoices/ - Create a new invoice."""
        return await self.request("POST", "/invoices/", body=data)

    async def get_invoices(self, **kwargs) -> dict:
        """GET /invoices/ - List all invoices."""
        return await self.request("GET", "/invoices/",
                                  query_params=kwargs)

    async def create_text2pay_invoice(self, data: dict) -> dict:
        """POST /invoices/text2pay - Create & Send text2pay invoice."""
        return await self.request("POST", "/invoices/text2pay", body=data)

    async def update_invoice_late_fees(self, invoice_id: str,
                                        data: dict) -> dict:
        """PATCH /invoices/{invoiceId}/late-fees-configuration"""
        return await self.request(
            "PATCH", f"/invoices/{invoice_id}/late-fees-configuration",
            body=data)

    async def update_invoice_payment_methods(self, invoice_id: str,
                                              data: dict) -> dict:
        """PATCH /invoices/{invoiceId}/payment-methods-configuration"""
        return await self.request(
            "PATCH",
            f"/invoices/{invoice_id}/payment-methods-configuration",
            body=data)

    async def get_invoice_schedule(self, schedule_id: str) -> dict:
        """GET /invoices/schedule/{scheduleId}"""
        return await self.request("GET",
                                  f"/invoices/schedule/{schedule_id}")

    async def update_invoice_schedule(self, schedule_id: str,
                                       data: dict) -> dict:
        """PUT /invoices/schedule/{scheduleId}"""
        return await self.request("PUT",
                                  f"/invoices/schedule/{schedule_id}",
                                  body=data)

    async def delete_invoice_schedule(self, schedule_id: str) -> dict:
        """DELETE /invoices/schedule/{scheduleId}"""
        return await self.request("DELETE",
                                  f"/invoices/schedule/{schedule_id}")

    async def update_and_schedule_invoice(self, schedule_id: str,
                                           data: dict) -> dict:
        """POST /invoices/schedule/{scheduleId}/updateAndSchedule"""
        return await self.request(
            "POST",
            f"/invoices/schedule/{schedule_id}/updateAndSchedule",
            body=data)

    async def manage_invoice_auto_payment(self, schedule_id: str,
                                           data: dict) -> dict:
        """POST /invoices/schedule/{scheduleId}/auto-payment"""
        return await self.request(
            "POST",
            f"/invoices/schedule/{schedule_id}/auto-payment",
            body=data)

    async def update_template_late_fees(self, template_id: str,
                                         data: dict) -> dict:
        """PATCH /invoices/template/{templateId}/late-fees-configuration"""
        return await self.request(
            "PATCH",
            f"/invoices/template/{template_id}/late-fees-configuration",
            body=data)

    async def update_template_payment_methods(self, template_id: str,
                                               data: dict) -> dict:
        """PATCH /invoices/template/{templateId}/payment-methods-configuration"""
        return await self.request(
            "PATCH",
            f"/invoices/template/{template_id}/payment-methods-configuration",
            body=data)

    # --- Estimates Extended ---

    async def get_estimate(self, estimate_id: str) -> dict:
        """GET /invoices/estimate/{estimateId} (from list, not dedicated)."""
        # Note: No dedicated GET for single estimate; use list with filters
        return await self.request("GET", "/invoices/estimate/list",
                                  query_params={"estimateId": estimate_id})

    async def update_estimate(self, estimate_id: str, data: dict) -> dict:
        """PUT /invoices/estimate/{estimateId}"""
        return await self.request("PUT",
                                  f"/invoices/estimate/{estimate_id}",
                                  body=data)

    async def delete_estimate(self, estimate_id: str) -> dict:
        """DELETE /invoices/estimate/{estimateId}"""
        return await self.request("DELETE",
                                  f"/invoices/estimate/{estimate_id}")

    async def generate_estimate_number(self, **kwargs) -> dict:
        """GET /invoices/estimate/number/generate"""
        return await self.request("GET",
                                  "/invoices/estimate/number/generate",
                                  query_params=kwargs)

    async def get_estimate_templates(self, **kwargs) -> dict:
        """GET /invoices/estimate/template"""
        return await self.request("GET", "/invoices/estimate/template",
                                  query_params=kwargs)

    async def create_estimate_template(self, data: dict) -> dict:
        """POST /invoices/estimate/template"""
        return await self.request("POST", "/invoices/estimate/template",
                                  body=data)

    # =========================================================================
    # PRODUCTS - Extended (Store, Reviews Count, Bulk Edit)
    # =========================================================================

    async def get_product_store_stats(self, store_id: str) -> dict:
        """GET /products/store/{storeId}/stats"""
        return await self.request("GET",
                                  f"/products/store/{store_id}/stats")

    async def include_product_in_store(self, store_id: str,
                                        data: dict) -> dict:
        """POST /products/store/{storeId}"""
        return await self.request("POST",
                                  f"/products/store/{store_id}",
                                  body=data)

    async def update_store_display_priorities(self, store_id: str,
                                              data: dict) -> dict:
        """POST /products/store/{storeId}/priority"""
        return await self.request("POST",
                                  f"/products/store/{store_id}/priority",
                                  body=data)

    async def get_product_price(self, product_id: str,
                                 price_id: str) -> dict:
        """GET /products/{productId}/price/{priceId}"""
        return await self.request(
            "GET", f"/products/{product_id}/price/{price_id}",
            query_params=self._loc())

    async def get_product_reviews_count(self, **kwargs) -> dict:
        """GET /products/reviews/count"""
        return await self.request("GET", "/products/reviews/count",
                                  query_params=kwargs)

    async def bulk_update_reviews(self, data: dict) -> dict:
        """POST /products/reviews/bulk-update"""
        return await self.request("POST", "/products/reviews/bulk-update",
                                  body=data)

    async def bulk_edit_products(self, data: dict) -> dict:
        """POST /products/bulk-update/edit - Bulk edit products and prices."""
        return await self.request("POST", "/products/bulk-update/edit",
                                  body=data)

    # =========================================================================
    # CALENDARS - Extended (Service Bookings, Resource GET, Notification CRUD)
    # =========================================================================

    # --- Service Bookings ---

    async def get_service_bookings(self, **kwargs) -> dict:
        """GET /calendars/services/bookings"""
        return await self.request("GET", "/calendars/services/bookings",
                                  query_params=self._loc(kwargs))

    async def create_service_booking(self, data: dict) -> dict:
        """POST /calendars/services/bookings"""
        return await self.request("POST", "/calendars/services/bookings",
                                  body=data)

    async def update_service_booking(self, booking_id: str,
                                      data: dict) -> dict:
        """PUT /calendars/services/bookings/{bookingId}"""
        return await self.request(
            "PUT", f"/calendars/services/bookings/{booking_id}",
            body=data)

    async def delete_service_booking(self, booking_id: str) -> dict:
        """DELETE /calendars/services/bookings/{bookingId}"""
        return await self.request(
            "DELETE", f"/calendars/services/bookings/{booking_id}")

    # --- Calendar Resource GET by ID ---

    async def get_calendar_resource(self, resource_type: str,
                                     resource_id: str) -> dict:
        """GET /calendars/resources/{resourceType}/{id}"""
        return await self.request(
            "GET", f"/calendars/resources/{resource_type}/{resource_id}",
            query_params=self._loc())

    # --- Calendar Notification CRUD ---

    async def get_calendar_notification(self, calendar_id: str,
                                         notification_id: str) -> dict:
        """GET /calendars/{calendarId}/notifications/{notificationId}"""
        return await self.request(
            "GET",
            f"/calendars/{calendar_id}/notifications/{notification_id}")

    async def update_calendar_notification(self, calendar_id: str,
                                            notification_id: str,
                                            data: dict) -> dict:
        """PUT /calendars/{calendarId}/notifications/{notificationId}"""
        return await self.request(
            "PUT",
            f"/calendars/{calendar_id}/notifications/{notification_id}",
            body=data)

    async def delete_calendar_notification(self, calendar_id: str,
                                            notification_id: str) -> dict:
        """DELETE /calendars/{calendarId}/notifications/{notificationId}"""
        return await self.request(
            "DELETE",
            f"/calendars/{calendar_id}/notifications/{notification_id}")

    # =========================================================================
    # CONVERSATIONS - Extended (Recordings, Transcription, Live Chat)
    # =========================================================================

    async def get_message_recording(self, message_id: str) -> dict:
        """GET /conversations/messages/{messageId}/locations/{locationId}/recording"""
        return await self.request(
            "GET",
            f"/conversations/messages/{message_id}/locations/"
            f"{self.location_id}/recording")

    async def get_message_transcription(self, message_id: str) -> dict:
        """GET /conversations/locations/{locationId}/messages/{messageId}/transcription"""
        return await self.request(
            "GET",
            f"/conversations/locations/{self.location_id}/messages/"
            f"{message_id}/transcription")

    async def download_message_transcription(self,
                                              message_id: str) -> dict:
        """GET /conversations/locations/{locationId}/messages/{messageId}/transcription/download"""
        return await self.request(
            "GET",
            f"/conversations/locations/{self.location_id}/messages/"
            f"{message_id}/transcription/download")

    async def live_chat_typing(self, data: dict) -> dict:
        """POST /conversations/providers/live-chat/typing"""
        return await self.request("POST",
                                  "/conversations/providers/live-chat/typing",
                                  body=data)

    async def cancel_scheduled_email(self, email_message_id: str) -> dict:
        """DELETE /conversations/messages/email/{emailMessageId}/schedule"""
        return await self.request(
            "DELETE",
            f"/conversations/messages/email/{email_message_id}/schedule")

    # =========================================================================
    # CONTACTS - Extended (Remove All Campaigns, Individual Task/Note CRUD)
    # =========================================================================

    async def remove_contact_from_all_campaigns(self,
                                                  contact_id: str) -> dict:
        """DELETE /contacts/{contactId}/campaigns/removeAll"""
        return await self.request(
            "DELETE", f"/contacts/{contact_id}/campaigns/removeAll")

    async def get_contact_note(self, contact_id: str,
                                note_id: str) -> dict:
        """GET /contacts/{contactId}/notes/{noteId}"""
        return await self.request(
            "GET", f"/contacts/{contact_id}/notes/{note_id}")

    async def get_contact_task(self, contact_id: str,
                                task_id: str) -> dict:
        """GET /contacts/{contactId}/tasks/{taskId}"""
        return await self.request(
            "GET", f"/contacts/{contact_id}/tasks/{task_id}")

    async def update_task_completed(self, contact_id: str,
                                     task_id: str,
                                     completed: bool) -> dict:
        """PUT /contacts/{contactId}/tasks/{taskId}/completed"""
        return await self.request(
            "PUT",
            f"/contacts/{contact_id}/tasks/{task_id}/completed",
            body={"completed": completed})

    # =========================================================================
    # LOCATIONS - Extended (Recurring Tasks, Timezones, Individual GETs)
    # =========================================================================

    async def get_location_timezones(self,
                                      location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/timezones"""
        loc = location_id or self.location_id
        return await self.request("GET", f"/locations/{loc}/timezones")

    async def create_recurring_task(self, data: dict,
                                     location_id: str | None = None) -> dict:
        """POST /locations/{locationId}/recurring-tasks"""
        loc = location_id or self.location_id
        return await self.request("POST",
                                  f"/locations/{loc}/recurring-tasks",
                                  body=data)

    async def get_recurring_task(self, task_id: str,
                                  location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/recurring-tasks/{id}"""
        loc = location_id or self.location_id
        return await self.request(
            "GET", f"/locations/{loc}/recurring-tasks/{task_id}")

    async def update_recurring_task(self, task_id: str, data: dict,
                                     location_id: str | None = None) -> dict:
        """PUT /locations/{locationId}/recurring-tasks/{id}"""
        loc = location_id or self.location_id
        return await self.request(
            "PUT", f"/locations/{loc}/recurring-tasks/{task_id}",
            body=data)

    async def delete_recurring_task(self, task_id: str,
                                     location_id: str | None = None) -> dict:
        """DELETE /locations/{locationId}/recurring-tasks/{id}"""
        loc = location_id or self.location_id
        return await self.request(
            "DELETE", f"/locations/{loc}/recurring-tasks/{task_id}")

    async def get_custom_field_by_id(self, field_id: str,
                                      location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/customFields/{customFieldId}"""
        loc = location_id or self.location_id
        return await self.request(
            "GET", f"/locations/{loc}/customFields/{field_id}")

    async def get_custom_value_by_id(self, value_id: str,
                                      location_id: str | None = None) -> dict:
        """GET /locations/{locationId}/customValues/{customValueId}"""
        loc = location_id or self.location_id
        return await self.request(
            "GET", f"/locations/{loc}/customValues/{value_id}")

    async def create_location(self, data: dict) -> dict:
        """POST /locations/ - Create a new sub-account/location."""
        return await self.request("POST", "/locations/", body=data)

    # =========================================================================
    # CUSTOM OBJECTS (Schemas & Records)
    # =========================================================================

    async def get_object_schemas(self, **kwargs) -> dict:
        """GET /objects/ - Get all objects for a location."""
        return await self.request("GET", "/objects/",
                                  query_params=self._loc(kwargs))

    async def get_object_schema(self, key: str) -> dict:
        """GET /objects/{key} - Get object schema by key/id."""
        return await self.request("GET", f"/objects/{key}",
                                  query_params=self._loc())

    async def create_custom_object(self, data: dict) -> dict:
        """POST /objects/ - Create custom object schema."""
        return await self.request("POST", "/objects/",
                                  body=self._loc_body(data))

    async def update_object_schema(self, key: str, data: dict) -> dict:
        """PUT /objects/{key} - Update object schema."""
        return await self.request("PUT", f"/objects/{key}",
                                  body=self._loc_body(data))

    async def create_object_record(self, schema_key: str,
                                    data: dict) -> dict:
        """POST /objects/{schemaKey}/records"""
        return await self.request("POST",
                                  f"/objects/{schema_key}/records",
                                  body=self._loc_body(data))

    async def get_object_record(self, schema_key: str,
                                 record_id: str) -> dict:
        """GET /objects/{schemaKey}/records/{id}"""
        return await self.request(
            "GET", f"/objects/{schema_key}/records/{record_id}",
            query_params=self._loc())

    async def update_object_record(self, schema_key: str,
                                    record_id: str, data: dict) -> dict:
        """PUT /objects/{schemaKey}/records/{id}"""
        return await self.request(
            "PUT", f"/objects/{schema_key}/records/{record_id}",
            body=self._loc_body(data))

    async def delete_object_record(self, schema_key: str,
                                    record_id: str) -> dict:
        """DELETE /objects/{schemaKey}/records/{id}"""
        return await self.request(
            "DELETE", f"/objects/{schema_key}/records/{record_id}",
            query_params=self._loc())

    async def search_object_records(self, schema_key: str,
                                     data: dict) -> dict:
        """POST /objects/{schemaKey}/records/search"""
        return await self.request(
            "POST", f"/objects/{schema_key}/records/search",
            body=self._loc_body(data))

    # =========================================================================
    # VOICE AI (Agents, Actions, Call Logs)
    # =========================================================================

    async def create_voice_agent(self, data: dict) -> dict:
        """POST /voice-ai/agents"""
        return await self.request("POST", "/voice-ai/agents",
                                  body=self._loc_body(data))

    async def get_voice_agents(self, **kwargs) -> dict:
        """GET /voice-ai/agents"""
        return await self.request("GET", "/voice-ai/agents",
                                  query_params=self._loc(kwargs))

    async def get_voice_agent(self, agent_id: str) -> dict:
        """GET /voice-ai/agents/{agentId}"""
        return await self.request("GET", f"/voice-ai/agents/{agent_id}",
                                  query_params=self._loc())

    async def update_voice_agent(self, agent_id: str, data: dict) -> dict:
        """PATCH /voice-ai/agents/{agentId}"""
        return await self.request("PATCH",
                                  f"/voice-ai/agents/{agent_id}",
                                  body=data)

    async def delete_voice_agent(self, agent_id: str) -> dict:
        """DELETE /voice-ai/agents/{agentId}"""
        return await self.request("DELETE",
                                  f"/voice-ai/agents/{agent_id}")

    async def create_voice_action(self, data: dict) -> dict:
        """POST /voice-ai/actions"""
        return await self.request("POST", "/voice-ai/actions",
                                  body=data)

    async def get_voice_action(self, action_id: str) -> dict:
        """GET /voice-ai/actions/{actionId}"""
        return await self.request("GET",
                                  f"/voice-ai/actions/{action_id}")

    async def update_voice_action(self, action_id: str,
                                   data: dict) -> dict:
        """PUT /voice-ai/actions/{actionId}"""
        return await self.request("PUT",
                                  f"/voice-ai/actions/{action_id}",
                                  body=data)

    async def delete_voice_action(self, action_id: str) -> dict:
        """DELETE /voice-ai/actions/{actionId}"""
        return await self.request("DELETE",
                                  f"/voice-ai/actions/{action_id}")

    async def get_voice_call_logs(self, **kwargs) -> dict:
        """GET /voice-ai/dashboard/call-logs"""
        return await self.request("GET", "/voice-ai/dashboard/call-logs",
                                  query_params=self._loc(kwargs))

    async def get_voice_call_log(self, call_id: str) -> dict:
        """GET /voice-ai/dashboard/call-logs/{callId}"""
        return await self.request("GET",
                                  f"/voice-ai/dashboard/call-logs/{call_id}",
                                  query_params=self._loc())

    # =========================================================================
    # STORE (Shipping Zones, Rates, Carriers, Settings)
    # =========================================================================

    # --- Shipping Zones ---

    async def create_shipping_zone(self, data: dict) -> dict:
        """POST /store/shipping-zone"""
        return await self.request("POST", "/store/shipping-zone",
                                  body=self._loc_body(data))

    async def get_shipping_zones(self, **kwargs) -> dict:
        """GET /store/shipping-zone"""
        params = {"altId": self.location_id, "altType": "location", **kwargs}
        return await self.request("GET", "/store/shipping-zone",
                                  query_params=params)

    async def get_shipping_zone(self, zone_id: str) -> dict:
        """GET /store/shipping-zone/{shippingZoneId}"""
        return await self.request("GET",
                                  f"/store/shipping-zone/{zone_id}",
                                  query_params=self._loc())

    async def update_shipping_zone(self, zone_id: str,
                                    data: dict) -> dict:
        """PUT /store/shipping-zone/{shippingZoneId}"""
        return await self.request("PUT",
                                  f"/store/shipping-zone/{zone_id}",
                                  body=data)

    async def delete_shipping_zone(self, zone_id: str) -> dict:
        """DELETE /store/shipping-zone/{shippingZoneId}"""
        return await self.request("DELETE",
                                  f"/store/shipping-zone/{zone_id}")

    # --- Shipping Rates ---

    async def get_available_shipping_rates(self, data: dict) -> dict:
        """POST /store/shipping-zone/shipping-rates - Get rates by country/amount."""
        return await self.request("POST",
                                  "/store/shipping-zone/shipping-rates",
                                  body=self._loc_body(data))

    async def create_shipping_rate(self, zone_id: str,
                                    data: dict) -> dict:
        """POST /store/shipping-zone/{shippingZoneId}/shipping-rate"""
        return await self.request(
            "POST",
            f"/store/shipping-zone/{zone_id}/shipping-rate",
            body=data)

    async def get_shipping_rates(self, zone_id: str) -> dict:
        """GET /store/shipping-zone/{shippingZoneId}/shipping-rate"""
        return await self.request(
            "GET",
            f"/store/shipping-zone/{zone_id}/shipping-rate")

    async def get_shipping_rate(self, zone_id: str,
                                 rate_id: str) -> dict:
        """GET /store/shipping-zone/{zoneId}/shipping-rate/{rateId}"""
        return await self.request(
            "GET",
            f"/store/shipping-zone/{zone_id}/shipping-rate/{rate_id}")

    async def update_shipping_rate(self, zone_id: str,
                                    rate_id: str, data: dict) -> dict:
        """PUT /store/shipping-zone/{zoneId}/shipping-rate/{rateId}"""
        return await self.request(
            "PUT",
            f"/store/shipping-zone/{zone_id}/shipping-rate/{rate_id}",
            body=data)

    async def delete_shipping_rate(self, zone_id: str,
                                    rate_id: str) -> dict:
        """DELETE /store/shipping-zone/{zoneId}/shipping-rate/{rateId}"""
        return await self.request(
            "DELETE",
            f"/store/shipping-zone/{zone_id}/shipping-rate/{rate_id}")

    # --- Shipping Carriers ---

    async def create_shipping_carrier(self, data: dict) -> dict:
        """POST /store/shipping-carrier"""
        return await self.request("POST", "/store/shipping-carrier",
                                  body=self._loc_body(data))

    async def get_shipping_carriers(self, **kwargs) -> dict:
        """GET /store/shipping-carrier"""
        params = {"altId": self.location_id, "altType": "location", **kwargs}
        return await self.request("GET", "/store/shipping-carrier",
                                  query_params=params)

    async def get_shipping_carrier(self, carrier_id: str) -> dict:
        """GET /store/shipping-carrier/{shippingCarrierId}"""
        return await self.request("GET",
                                  f"/store/shipping-carrier/{carrier_id}",
                                  query_params=self._loc())

    async def update_shipping_carrier(self, carrier_id: str,
                                       data: dict) -> dict:
        """PUT /store/shipping-carrier/{shippingCarrierId}"""
        return await self.request("PUT",
                                  f"/store/shipping-carrier/{carrier_id}",
                                  body=data)

    async def delete_shipping_carrier(self, carrier_id: str) -> dict:
        """DELETE /store/shipping-carrier/{shippingCarrierId}"""
        return await self.request("DELETE",
                                  f"/store/shipping-carrier/{carrier_id}")

    # --- Store Settings ---

    async def get_store_settings(self, **kwargs) -> dict:
        """GET /store/store-setting"""
        params = {"altId": self.location_id, "altType": "location", **kwargs}
        return await self.request("GET", "/store/store-setting",
                                  query_params=params)

    async def update_store_settings(self, data: dict) -> dict:
        """POST /store/store-setting"""
        return await self.request("POST", "/store/store-setting",
                                  body=self._loc_body(data))

    # =========================================================================
    # CUSTOM MENUS
    # =========================================================================

    async def get_custom_menus(self) -> dict:
        """GET /custom-menus/"""
        return await self.request("GET", "/custom-menus/",
                                  query_params=self._loc())

    async def create_custom_menu(self, data: dict) -> dict:
        """POST /custom-menus/"""
        return await self.request("POST", "/custom-menus/",
                                  body=self._loc_body(data))

    async def get_custom_menu(self, menu_id: str) -> dict:
        """GET /custom-menus/{customMenuId}"""
        return await self.request("GET", f"/custom-menus/{menu_id}")

    async def update_custom_menu(self, menu_id: str, data: dict) -> dict:
        """PUT /custom-menus/{customMenuId}"""
        return await self.request("PUT", f"/custom-menus/{menu_id}",
                                  body=data)

    async def delete_custom_menu(self, menu_id: str) -> dict:
        """DELETE /custom-menus/{customMenuId}"""
        return await self.request("DELETE", f"/custom-menus/{menu_id}")

    # =========================================================================
    # DOCUMENTS / PROPOSALS
    # =========================================================================

    async def get_documents(self, **kwargs) -> dict:
        """GET /proposals/document - List documents."""
        return await self.request("GET", "/proposals/document",
                                  query_params=self._loc(kwargs))

    async def send_document(self, data: dict) -> dict:
        """POST /proposals/document/send"""
        return await self.request("POST", "/proposals/document/send",
                                  body=self._loc_body(data))

    async def get_document_templates(self, **kwargs) -> dict:
        """GET /proposals/templates"""
        return await self.request("GET", "/proposals/templates",
                                  query_params=self._loc(kwargs))

    async def send_document_template(self, data: dict) -> dict:
        """POST /proposals/templates/send"""
        return await self.request("POST", "/proposals/templates/send",
                                  body=self._loc_body(data))

    # =========================================================================
    # PHONE SYSTEM
    # =========================================================================

    async def get_number_pools(self, **kwargs) -> dict:
        """GET /phone-system/number-pools"""
        return await self.request("GET", "/phone-system/number-pools",
                                  query_params=self._loc(kwargs))

    async def get_active_numbers(self,
                                  location_id: str | None = None) -> dict:
        """GET /phone-system/numbers/location/{locationId}"""
        loc = location_id or self.location_id
        return await self.request("GET",
                                  f"/phone-system/numbers/location/{loc}")

    # =========================================================================
    # EMAIL ISV (Verification)
    # =========================================================================

    async def verify_email(self, data: dict) -> dict:
        """POST /email/verify - Email verification / deliverability check."""
        return await self.request("POST", "/email/verify", body=data)

    # =========================================================================
    # MARKETPLACE / BILLING
    # =========================================================================

    async def create_billing_charge(self, data: dict) -> dict:
        """POST /marketplace/billing/charges"""
        return await self.request("POST",
                                  "/marketplace/billing/charges",
                                  body=data)

    async def get_billing_charges(self, **kwargs) -> dict:
        """GET /marketplace/billing/charges"""
        return await self.request("GET",
                                  "/marketplace/billing/charges",
                                  query_params=kwargs)

    async def delete_billing_charge(self, charge_id: str) -> dict:
        """DELETE /marketplace/billing/charges/{chargeId}"""
        return await self.request("DELETE",
                                  f"/marketplace/billing/charges/{charge_id}")

    async def get_billing_charge(self, charge_id: str) -> dict:
        """GET /marketplace/billing/charges/{chargeId}"""
        return await self.request("GET",
                                  f"/marketplace/billing/charges/{charge_id}")

    async def check_has_funds(self, **kwargs) -> dict:
        """GET /marketplace/billing/charges/has-funds"""
        return await self.request("GET",
                                  "/marketplace/billing/charges/has-funds",
                                  query_params=kwargs)

    async def uninstall_app(self, app_id: str) -> dict:
        """DELETE /marketplace/app/{appId}/installations"""
        return await self.request("DELETE",
                                  f"/marketplace/app/{app_id}/installations")

    async def get_app_installer_details(self, app_id: str) -> dict:
        """GET /marketplace/app/{appId}/installations"""
        return await self.request("GET",
                                  f"/marketplace/app/{app_id}/installations")

    # =========================================================================
    # SOCIAL MEDIA - Extended (Google Business Locations)
    # =========================================================================

    async def get_google_business_locations(self,
                                             account_id: str) -> dict:
        """GET /social-media-posting/oauth/{locationId}/google/locations/{accountId}"""
        return await self.request(
            "GET",
            f"/social-media-posting/oauth/{self.location_id}/google/"
            f"locations/{account_id}")

    # =========================================================================
    # MISSING ENDPOINTS — FULL COVERAGE ADDITIONS
    # =========================================================================

    # ----- CONTACTS: Advanced Search & Bulk -----

    async def search_contacts_advanced(self, data: dict) -> dict:
        """POST /contacts/search — Advanced search with filter combinations."""
        body = {"locationId": self.location_id, **data}
        return await self.request("POST", "/contacts/search", body=body)

    async def get_duplicate_contacts(self, **kwargs) -> dict:
        """GET /contacts/search/duplicate — Find duplicate contacts."""
        params = self._loc(kwargs)
        return await self.request("GET", "/contacts/search/duplicate",
                                  query_params=params)

    async def get_contacts_by_business(self, business_id: str,
                                        **kwargs) -> dict:
        """GET /contacts/business/{businessId}"""
        return await self.request("GET",
                                  f"/contacts/business/{business_id}",
                                  query_params=kwargs)

    async def bulk_update_contact_business(self, data: dict) -> dict:
        """POST /contacts/bulk/business — Add/remove contacts from business."""
        return await self.request("POST", "/contacts/bulk/business",
                                  body=self._loc_body(data))

    async def bulk_update_contact_tags(self, tag_type: str,
                                        data: dict) -> dict:
        """POST /contacts/bulk/tags/update/{type} — Bulk add/remove tags."""
        return await self.request("POST",
                                  f"/contacts/bulk/tags/update/{tag_type}",
                                  body=self._loc_body(data))

    # ----- CONTACTS: Followers -----

    async def add_contact_followers(self, contact_id: str,
                                     data: dict) -> dict:
        """POST /contacts/{contactId}/followers"""
        return await self.request("POST",
                                  f"/contacts/{contact_id}/followers",
                                  body=data)

    async def remove_contact_followers(self, contact_id: str,
                                        data: dict) -> dict:
        """DELETE /contacts/{contactId}/followers"""
        return await self.request("DELETE",
                                  f"/contacts/{contact_id}/followers",
                                  body=data)

    # ----- CONTACTS: Single Note / Task by ID -----

    async def get_contact_note(self, contact_id: str,
                                note_id: str) -> dict:
        """GET /contacts/{contactId}/notes/{id}"""
        return await self.request("GET",
                                  f"/contacts/{contact_id}/notes/{note_id}")

    async def update_contact_note(self, contact_id: str, note_id: str,
                                   data: dict) -> dict:
        """PUT /contacts/{contactId}/notes/{id}"""
        return await self.request("PUT",
                                  f"/contacts/{contact_id}/notes/{note_id}",
                                  body=data)

    async def delete_contact_note(self, contact_id: str,
                                   note_id: str) -> dict:
        """DELETE /contacts/{contactId}/notes/{id}"""
        return await self.request("DELETE",
                                  f"/contacts/{contact_id}/notes/{note_id}")

    async def get_contact_task(self, contact_id: str,
                                task_id: str) -> dict:
        """GET /contacts/{contactId}/tasks/{taskId}"""
        return await self.request("GET",
                                  f"/contacts/{contact_id}/tasks/{task_id}")

    async def update_contact_task(self, contact_id: str, task_id: str,
                                   data: dict) -> dict:
        """PUT /contacts/{contactId}/tasks/{taskId}"""
        return await self.request("PUT",
                                  f"/contacts/{contact_id}/tasks/{task_id}",
                                  body=data)

    async def delete_contact_task(self, contact_id: str,
                                   task_id: str) -> dict:
        """DELETE /contacts/{contactId}/tasks/{taskId}"""
        return await self.request("DELETE",
                                  f"/contacts/{contact_id}/tasks/{task_id}")

    async def update_task_completed(self, contact_id: str, task_id: str,
                                     data: dict) -> dict:
        """PUT /contacts/{contactId}/tasks/{taskId}/completed"""
        return await self.request(
            "PUT", f"/contacts/{contact_id}/tasks/{task_id}/completed",
            body=data)

    # ----- CONTACTS: Campaign / Workflow Extended -----

    async def remove_contact_from_all_campaigns(self,
                                                  contact_id: str) -> dict:
        """DELETE /contacts/{contactId}/campaigns/removeAll"""
        return await self.request(
            "DELETE", f"/contacts/{contact_id}/campaigns/removeAll")

    # ----- CALENDAR: Groups (full) -----

    async def get_calendar_groups(self) -> dict:
        """GET /calendars/groups"""
        return await self.request("GET", "/calendars/groups",
                                  query_params=self._loc())

    async def create_calendar_group(self, data: dict) -> dict:
        """POST /calendars/groups"""
        return await self.request("POST", "/calendars/groups",
                                  body=self._loc_body(data))

    async def validate_calendar_group_slug(self, data: dict) -> dict:
        """POST /calendars/groups/validate-slug"""
        return await self.request("POST",
                                  "/calendars/groups/validate-slug",
                                  body=self._loc_body(data))

    async def update_calendar_group(self, group_id: str,
                                     data: dict) -> dict:
        """PUT /calendars/groups/{groupId}"""
        return await self.request("PUT",
                                  f"/calendars/groups/{group_id}",
                                  body=data)

    async def delete_calendar_group(self, group_id: str) -> dict:
        """DELETE /calendars/groups/{groupId}"""
        return await self.request("DELETE",
                                  f"/calendars/groups/{group_id}")

    async def update_calendar_group_status(self, group_id: str,
                                            data: dict) -> dict:
        """PUT /calendars/groups/{groupId}/status"""
        return await self.request("PUT",
                                  f"/calendars/groups/{group_id}/status",
                                  body=data)

    # ----- CALENDAR: Appointment Notes -----

    async def get_appointment_notes(self, appointment_id: str) -> dict:
        """GET /calendars/appointments/{appointmentId}/notes"""
        return await self.request(
            "GET", f"/calendars/appointments/{appointment_id}/notes")

    async def create_appointment_note(self, appointment_id: str,
                                       data: dict) -> dict:
        """POST /calendars/appointments/{appointmentId}/notes"""
        return await self.request(
            "POST", f"/calendars/appointments/{appointment_id}/notes",
            body=data)

    async def update_appointment_note(self, appointment_id: str,
                                       note_id: str, data: dict) -> dict:
        """PUT /calendars/appointments/{appointmentId}/notes/{noteId}"""
        return await self.request(
            "PUT",
            f"/calendars/appointments/{appointment_id}/notes/{note_id}",
            body=data)

    async def delete_appointment_note(self, appointment_id: str,
                                       note_id: str) -> dict:
        """DELETE /calendars/appointments/{appointmentId}/notes/{noteId}"""
        return await self.request(
            "DELETE",
            f"/calendars/appointments/{appointment_id}/notes/{note_id}")

    # ----- OPPORTUNITIES: Followers -----

    async def add_opportunity_followers(self, opportunity_id: str,
                                         data: dict) -> dict:
        """POST /opportunities/{id}/followers"""
        return await self.request(
            "POST", f"/opportunities/{opportunity_id}/followers",
            body=data)

    async def remove_opportunity_followers(self, opportunity_id: str,
                                            data: dict) -> dict:
        """DELETE /opportunities/{id}/followers"""
        return await self.request(
            "DELETE", f"/opportunities/{opportunity_id}/followers",
            body=data)

    # ----- FUNNELS: Redirects (full) -----

    async def get_redirects(self, **kwargs) -> dict:
        """GET /funnels/lookup/redirect/list"""
        params = self._loc(kwargs)
        return await self.request("GET", "/funnels/lookup/redirect/list",
                                  query_params=params)

    async def create_redirect(self, data: dict) -> dict:
        """POST /funnels/lookup/redirect"""
        return await self.request("POST", "/funnels/lookup/redirect",
                                  body=self._loc_body(data))

    async def update_redirect(self, redirect_id: str,
                               data: dict) -> dict:
        """PATCH /funnels/lookup/redirect/{id}"""
        return await self.request("PATCH",
                                  f"/funnels/lookup/redirect/{redirect_id}",
                                  body=data)

    async def delete_redirect(self, redirect_id: str) -> dict:
        """DELETE /funnels/lookup/redirect/{id}"""
        return await self.request("DELETE",
                                  f"/funnels/lookup/redirect/{redirect_id}")

    async def get_funnel_pages(self, **kwargs) -> dict:
        """GET /funnels/page — Get pages by funnel ID."""
        return await self.request("GET", "/funnels/page",
                                  query_params=self._loc(kwargs))

    async def get_funnel_page_count(self, **kwargs) -> dict:
        """GET /funnels/page/count"""
        return await self.request("GET", "/funnels/page/count",
                                  query_params=self._loc(kwargs))

    # ----- PRODUCTS: Full Coverage -----

    async def get_product_price(self, product_id: str,
                                 price_id: str) -> dict:
        """GET /products/{productId}/price/{priceId}"""
        return await self.request(
            "GET", f"/products/{product_id}/price/{price_id}")

    async def get_collection(self, collection_id: str) -> dict:
        """GET /products/collections/{collectionId}"""
        return await self.request("GET",
                                  f"/products/collections/{collection_id}")

    async def bulk_edit_products(self, data: dict) -> dict:
        """POST /products/bulk-update/edit — Max 30 entities."""
        return await self.request("POST", "/products/bulk-update/edit",
                                  body=self._loc_body(data))

    async def get_product_reviews_count(self, **kwargs) -> dict:
        """GET /products/reviews/count"""
        return await self.request("GET", "/products/reviews/count",
                                  query_params=self._loc(kwargs))

    async def bulk_update_reviews(self, data: dict) -> dict:
        """POST /products/reviews/bulk-update"""
        return await self.request("POST", "/products/reviews/bulk-update",
                                  body=self._loc_body(data))

    async def get_product_store_stats(self, store_id: str) -> dict:
        """GET /products/store/{storeId}/stats"""
        params = {"locationId": self.location_id}
        return await self.request("GET",
                                  f"/products/store/{store_id}/stats",
                                  query_params=params)

    async def include_product_in_store(self, store_id: str,
                                        data: dict) -> dict:
        """POST /products/store/{storeId}"""
        return await self.request("POST",
                                  f"/products/store/{store_id}",
                                  body=self._loc_body(data))

    async def update_store_display_priorities(self, store_id: str,
                                               data: dict) -> dict:
        """POST /products/store/{storeId}/priority"""
        return await self.request("POST",
                                  f"/products/store/{store_id}/priority",
                                  body=self._loc_body(data))

    async def get_inventory(self, **kwargs) -> dict:
        """GET /products/inventory"""
        return await self.request("GET", "/products/inventory",
                                  query_params=self._loc(kwargs))

    async def update_inventory(self, data: dict) -> dict:
        """POST /products/inventory — Bulk update inventory."""
        return await self.request("POST", "/products/inventory",
                                  body=self._loc_body(data))

    # ----- INVOICES: Full Coverage -----

    async def get_invoice_template(self, template_id: str) -> dict:
        """GET /invoices/template/{templateId}"""
        return await self.request("GET",
                                  f"/invoices/template/{template_id}",
                                  query_params=self._loc())

    async def update_invoice_schedule(self, schedule_id: str,
                                       data: dict) -> dict:
        """PUT /invoices/schedule/{scheduleId}"""
        return await self.request("PUT",
                                  f"/invoices/schedule/{schedule_id}",
                                  body=self._loc_body(data))

    async def delete_invoice_schedule(self, schedule_id: str) -> dict:
        """DELETE /invoices/schedule/{scheduleId}"""
        return await self.request("DELETE",
                                  f"/invoices/schedule/{schedule_id}",
                                  query_params=self._loc())

    async def get_invoice_schedule(self, schedule_id: str) -> dict:
        """GET /invoices/schedule/{scheduleId}"""
        return await self.request("GET",
                                  f"/invoices/schedule/{schedule_id}",
                                  query_params=self._loc())

    async def update_and_schedule_invoice(self, schedule_id: str,
                                           data: dict) -> dict:
        """POST /invoices/schedule/{scheduleId}/updateAndSchedule"""
        return await self.request(
            "POST",
            f"/invoices/schedule/{schedule_id}/updateAndSchedule",
            body=self._loc_body(data))

    async def manage_invoice_auto_payment(self, schedule_id: str,
                                           data: dict) -> dict:
        """POST /invoices/schedule/{scheduleId}/auto-payment"""
        return await self.request(
            "POST",
            f"/invoices/schedule/{schedule_id}/auto-payment",
            body=self._loc_body(data))

    async def update_invoice_late_fees(self, invoice_id: str,
                                        data: dict) -> dict:
        """PATCH /invoices/{invoiceId}/late-fees-configuration"""
        return await self.request(
            "PATCH",
            f"/invoices/{invoice_id}/late-fees-configuration",
            body=self._loc_body(data))

    async def update_invoice_payment_methods(self, invoice_id: str,
                                              data: dict) -> dict:
        """PATCH /invoices/{invoiceId}/payment-methods-configuration"""  # noqa
        return await self.request(
            "PATCH",
            f"/invoices/{invoice_id}/payment-methods-configuration",
            body=self._loc_body(data))

    async def update_template_late_fees(self, template_id: str,
                                         data: dict) -> dict:
        """PATCH /invoices/template/{templateId}/late-fees-configuration"""
        return await self.request(
            "PATCH",
            f"/invoices/template/{template_id}/late-fees-configuration",
            body=self._loc_body(data))

    async def update_template_payment_methods(self, template_id: str,
                                               data: dict) -> dict:
        """PATCH /invoices/template/{templateId}/payment-methods-configuration"""  # noqa
        return await self.request(
            "PATCH",
            f"/invoices/template/{template_id}/"
            "payment-methods-configuration",
            body=self._loc_body(data))

    async def update_estimate(self, estimate_id: str,
                               data: dict) -> dict:
        """PUT /invoices/estimate/{estimateId}"""
        return await self.request("PUT",
                                  f"/invoices/estimate/{estimate_id}",
                                  body=self._loc_body(data))

    async def delete_estimate(self, estimate_id: str) -> dict:
        """DELETE /invoices/estimate/{estimateId}"""
        return await self.request("DELETE",
                                  f"/invoices/estimate/{estimate_id}",
                                  query_params=self._loc())

    async def get_estimate(self, estimate_id: str) -> dict:
        """GET /invoices/estimate/{estimateId} — via list endpoint."""
        return await self.request("GET", "/invoices/estimate/list",
                                  query_params=self._loc(
                                      {"estimateId": estimate_id}))

    async def generate_estimate_number(self) -> dict:
        """GET /invoices/estimate/number/generate"""
        return await self.request("GET",
                                  "/invoices/estimate/number/generate",
                                  query_params=self._loc())

    async def get_estimate_templates(self, **kwargs) -> dict:
        """GET /invoices/estimate/template"""
        return await self.request("GET", "/invoices/estimate/template",
                                  query_params=self._loc(kwargs))

    async def create_estimate_template(self, data: dict) -> dict:
        """POST /invoices/estimate/template"""
        return await self.request("POST", "/invoices/estimate/template",
                                  body=self._loc_body(data))

    # ----- PAYMENTS: Full Coverage -----

    async def get_coupon(self, **kwargs) -> dict:
        """GET /payments/coupon — Get single coupon."""
        params = {"altId": self.location_id, "altType": "location",
                  **kwargs}
        return await self.request("GET", "/payments/coupon",
                                  query_params=params)

    async def record_order_payment(self, order_id: str,
                                    data: dict) -> dict:
        """POST /payments/orders/{orderId}/record-payment"""
        return await self.request(
            "POST", f"/payments/orders/{order_id}/record-payment",
            body=data)

    async def get_order_notes(self, order_id: str) -> dict:
        """GET /payments/orders/{orderId}/notes"""
        return await self.request("GET",
                                  f"/payments/orders/{order_id}/notes")

    async def create_whitelabel_integration(self, data: dict) -> dict:
        """POST /payments/integrations/provider/whitelabel"""
        return await self.request(
            "POST", "/payments/integrations/provider/whitelabel",
            body=data)

    async def get_whitelabel_integrations(self, **kwargs) -> dict:
        """GET /payments/integrations/provider/whitelabel"""
        return await self.request(
            "GET", "/payments/integrations/provider/whitelabel",
            query_params=self._loc(kwargs))

    async def create_custom_provider(self, data: dict) -> dict:
        """POST /payments/custom-provider/provider"""
        return await self.request("POST",
                                  "/payments/custom-provider/provider",
                                  body=data)

    async def delete_custom_provider(self, **kwargs) -> dict:
        """DELETE /payments/custom-provider/provider"""
        return await self.request("DELETE",
                                  "/payments/custom-provider/provider",
                                  query_params=kwargs)

    async def get_custom_provider_config(self, **kwargs) -> dict:
        """GET /payments/custom-provider/connect"""
        return await self.request("GET",
                                  "/payments/custom-provider/connect",
                                  query_params=self._loc(kwargs))

    async def create_custom_provider_config(self, data: dict) -> dict:
        """POST /payments/custom-provider/connect"""
        return await self.request("POST",
                                  "/payments/custom-provider/connect",
                                  body=self._loc_body(data))

    async def disconnect_custom_provider(self, data: dict) -> dict:
        """POST /payments/custom-provider/disconnect"""
        return await self.request("POST",
                                  "/payments/custom-provider/disconnect",
                                  body=self._loc_body(data))

    # ----- BLOGS: Full Coverage -----

    async def check_blog_url_slug(self, **kwargs) -> dict:
        """GET /blogs/posts/url-slug-exists"""
        return await self.request("GET", "/blogs/posts/url-slug-exists",
                                  query_params=self._loc(kwargs))

    async def get_blog_authors(self, **kwargs) -> dict:
        """GET /blogs/authors"""
        return await self.request("GET", "/blogs/authors",
                                  query_params=self._loc(kwargs))

    async def get_blog_categories(self, **kwargs) -> dict:
        """GET /blogs/categories"""
        return await self.request("GET", "/blogs/categories",
                                  query_params=self._loc(kwargs))

    # ----- MEDIA: Full Coverage -----

    async def update_media_file(self, media_id: str,
                                 data: dict) -> dict:
        """POST /medias/{id} — Update metadata."""
        return await self.request("POST", f"/medias/{media_id}",
                                  body=self._loc_body(data))

    async def bulk_update_media(self, data: dict) -> dict:
        """PUT /medias/update-files"""
        return await self.request("PUT", "/medias/update-files",
                                  body=self._loc_body(data))

    # ----- USERS: Full Coverage -----

    async def filter_users_by_email(self, data: dict) -> dict:
        """POST /users/search/filter-by-email"""
        return await self.request("POST",
                                  "/users/search/filter-by-email",
                                  body=data)

    # ----- LOCATIONS: Full Coverage -----

    async def search_locations(self, **kwargs) -> dict:
        """GET /locations/search"""
        return await self.request("GET", "/locations/search",
                                  query_params=kwargs)

    async def delete_location(self, location_id: str) -> dict:
        """DELETE /locations/{locationId}"""
        return await self.request("DELETE",
                                  f"/locations/{location_id}")

    async def get_tag_by_id(self, tag_id: str) -> dict:
        """GET /locations/{locationId}/tags/{tagId}"""
        return await self.request(
            "GET",
            f"/locations/{self.location_id}/tags/{tag_id}")

    async def search_tasks(self, data: dict) -> dict:
        """POST /locations/{locationId}/tasks/search"""
        return await self.request(
            "POST",
            f"/locations/{self.location_id}/tasks/search",
            body=data)

    # ----- SNAPSHOTS: Full Coverage -----

    async def get_snapshot_push_latest(self, snapshot_id: str,
                                        location_id: str) -> dict:
        """GET /snapshots/snapshot-status/{snapshotId}/location/{locationId}"""
        return await self.request(
            "GET",
            f"/snapshots/snapshot-status/{snapshot_id}/"
            f"location/{location_id}")

    # ----- CUSTOM OBJECTS: Full Coverage (ensuring all exist) -----

    async def get_object_schema_by_key(self, key: str) -> dict:
        """GET /objects/{key}"""
        return await self.request("GET", f"/objects/{key}",
                                  query_params=self._loc())

    async def update_object_schema(self, key: str, data: dict) -> dict:
        """PUT /objects/{key}"""
        return await self.request("PUT", f"/objects/{key}",
                                  body=self._loc_body(data))

    # ----- ASSOCIATIONS: Full Coverage -----

    async def get_association_by_key(self, key_name: str) -> dict:
        """GET /associations/key/{key_name}"""
        return await self.request("GET",
                                  f"/associations/key/{key_name}",
                                  query_params=self._loc())

    async def get_associations_by_object(self, object_key: str,
                                          **kwargs) -> dict:
        """GET /associations/objectKey/{objectKey}"""
        params = self._loc(kwargs)
        return await self.request("GET",
                                  f"/associations/objectKey/{object_key}",
                                  query_params=params)

    # ----- SOCIAL MEDIA: Extended -----

    async def bulk_delete_social_posts(self, data: dict) -> dict:
        """POST /social-media-posting/{locationId}/posts/bulk-delete"""
        return await self.request(
            "POST",
            f"/social-media-posting/{self.location_id}/posts/bulk-delete",
            body=data)

    # ----- FORMS: Upload Custom Files -----

    async def upload_form_custom_files(self, data: dict) -> dict:
        """POST /forms/upload-custom-files"""
        return await self.request("POST", "/forms/upload-custom-files",
                                  body=self._loc_body(data))

    # ----- CONVERSATIONS: Extended (ensuring all exist) -----

    async def get_email_message(self, email_id: str) -> dict:
        """GET /conversations/messages/email/{id}"""
        return await self.request(
            "GET", f"/conversations/messages/email/{email_id}")

    async def cancel_scheduled_email(self, email_message_id: str) -> dict:
        """DELETE /conversations/messages/email/{emailMessageId}/schedule"""
        return await self.request(
            "DELETE",
            f"/conversations/messages/email/{email_message_id}/schedule")

    async def live_chat_typing(self, data: dict) -> dict:
        """POST /conversations/providers/live-chat/typing"""
        return await self.request(
            "POST", "/conversations/providers/live-chat/typing",
            body=self._loc_body(data))

    async def get_message_recording(self, message_id: str) -> dict:
        """GET /conversations/messages/{messageId}/locations/{locationId}/recording"""
        return await self.request(
            "GET",
            f"/conversations/messages/{message_id}/locations/"
            f"{self.location_id}/recording")

    async def get_message_transcription(self, message_id: str) -> dict:
        """GET /conversations/locations/{locationId}/messages/{messageId}/transcription"""
        return await self.request(
            "GET",
            f"/conversations/locations/{self.location_id}/messages/"
            f"{message_id}/transcription")

    async def download_message_transcription(self,
                                              message_id: str) -> dict:
        """GET .../transcription/download"""
        return await self.request(
            "GET",
            f"/conversations/locations/{self.location_id}/messages/"
            f"{message_id}/transcription/download")

    # ----- STORE: Full Coverage (Shipping Zones, Rates, Carriers) -----

    async def create_store_setting(self, data: dict) -> dict:
        """POST /store/store-setting"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request("POST", "/store/store-setting",
                                  body=data, query_params=params)

    async def get_shipping_zone(self, zone_id: str) -> dict:
        """GET /store/shipping-zone/{shippingZoneId}"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request("GET",
                                  f"/store/shipping-zone/{zone_id}",
                                  query_params=params)

    async def get_shipping_rate(self, zone_id: str,
                                 rate_id: str) -> dict:
        """GET /store/shipping-zone/{zoneId}/shipping-rate/{rateId}"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request(
            "GET",
            f"/store/shipping-zone/{zone_id}/shipping-rate/{rate_id}",
            query_params=params)

    async def update_shipping_rate(self, zone_id: str, rate_id: str,
                                    data: dict) -> dict:
        """PUT /store/shipping-zone/{zoneId}/shipping-rate/{rateId}"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request(
            "PUT",
            f"/store/shipping-zone/{zone_id}/shipping-rate/{rate_id}",
            body=data, query_params=params)

    async def delete_shipping_rate(self, zone_id: str,
                                    rate_id: str) -> dict:
        """DELETE /store/shipping-zone/{zoneId}/shipping-rate/{rateId}"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request(
            "DELETE",
            f"/store/shipping-zone/{zone_id}/shipping-rate/{rate_id}",
            query_params=params)

    async def get_shipping_carrier(self, carrier_id: str) -> dict:
        """GET /store/shipping-carrier/{shippingCarrierId}"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request(
            "GET", f"/store/shipping-carrier/{carrier_id}",
            query_params=params)

    async def update_shipping_carrier(self, carrier_id: str,
                                       data: dict) -> dict:
        """PUT /store/shipping-carrier/{shippingCarrierId}"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request(
            "PUT", f"/store/shipping-carrier/{carrier_id}",
            body=data, query_params=params)

    async def delete_shipping_carrier(self, carrier_id: str) -> dict:
        """DELETE /store/shipping-carrier/{shippingCarrierId}"""
        params = {"altId": self.location_id, "altType": "location"}
        return await self.request(
            "DELETE", f"/store/shipping-carrier/{carrier_id}",
            query_params=params)

    async def get_available_shipping_rates(self, data: dict) -> dict:
        """POST /store/shipping-zone/shipping-rates — Rates by country."""
        return await self.request(
            "POST", "/store/shipping-zone/shipping-rates",
            body=self._loc_body(data))

    # ----- VOICE AI: Full Coverage -----

    async def get_voice_call_log(self, call_id: str) -> dict:
        """GET /voice-ai/dashboard/call-logs/{callId}"""
        return await self.request(
            "GET", f"/voice-ai/dashboard/call-logs/{call_id}",
            query_params=self._loc())

    # ----- CUSTOM FIELDS V2: Full Coverage -----

    async def get_custom_field_v2(self, field_id: str) -> dict:
        """GET /custom-fields/{id}"""
        return await self.request("GET",
                                  f"/custom-fields/{field_id}")

    async def create_custom_field_v2(self, data: dict) -> dict:
        """POST /custom-fields/"""
        return await self.request("POST", "/custom-fields/",
                                  body=self._loc_body(data))

    async def update_custom_field_v2(self, field_id: str,
                                      data: dict) -> dict:
        """PUT /custom-fields/{id}"""
        return await self.request("PUT",
                                  f"/custom-fields/{field_id}",
                                  body=data)

    async def delete_custom_field_v2(self, field_id: str) -> dict:
        """DELETE /custom-fields/{id}"""
        return await self.request("DELETE",
                                  f"/custom-fields/{field_id}")

    async def get_custom_fields_by_object(self, object_key: str,
                                           **kwargs) -> dict:
        """GET /custom-fields/object-key/{objectKey}"""
        return await self.request(
            "GET", f"/custom-fields/object-key/{object_key}",
            query_params=self._loc(kwargs))

    async def create_custom_field_folder(self, data: dict) -> dict:
        """POST /custom-fields/folder"""
        return await self.request("POST", "/custom-fields/folder",
                                  body=self._loc_body(data))

    async def update_custom_field_folder(self, folder_id: str,
                                          data: dict) -> dict:
        """PUT /custom-fields/folder/{id}"""
        return await self.request("PUT",
                                  f"/custom-fields/folder/{folder_id}",
                                  body=data)

    async def delete_custom_field_folder(self, folder_id: str) -> dict:
        """DELETE /custom-fields/folder/{id}"""
        return await self.request("DELETE",
                                  f"/custom-fields/folder/{folder_id}")

    # ----- EMAILS (Campaigns / Builder) -----

    async def get_email_campaigns(self, **kwargs) -> dict:
        """GET /emails/schedule — Get email campaigns."""
        return await self.request("GET", "/emails/schedule",
                                  query_params=self._loc(kwargs))

    async def create_email_template(self, data: dict) -> dict:
        """POST /emails/builder"""
        return await self.request("POST", "/emails/builder",
                                  body=self._loc_body(data))

    async def get_email_templates(self, **kwargs) -> dict:
        """GET /emails/builder"""
        return await self.request("GET", "/emails/builder",
                                  query_params=self._loc(kwargs))

    async def delete_email_template(self, template_id: str) -> dict:
        """DELETE /emails/builder/{locationId}/{templateId}"""
        return await self.request(
            "DELETE",
            f"/emails/builder/{self.location_id}/{template_id}")

    async def update_email_template_data(self, data: dict) -> dict:
        """POST /emails/builder/data"""
        return await self.request("POST", "/emails/builder/data",
                                  body=self._loc_body(data))

    # ----- COURSES -----

    async def import_courses(self, data: dict) -> dict:
        """POST /courses/courses-exporter/public/import"""
        return await self.request(
            "POST", "/courses/courses-exporter/public/import",
            body=data)

    # ----- COMPANIES -----

    async def get_company(self, company_id: str) -> dict:
        """GET /companies/{companyId}"""
        return await self.request("GET",
                                  f"/companies/{company_id}")

    # ----- KNOWLEDGE BASE -----

    async def get_knowledge_bases(self) -> dict:
        """GET /knowledge-bases/ - List all knowledge bases."""
        return await self.request("GET", "/knowledge-bases/",
                                  query_params=self._loc())

    async def create_knowledge_base(self, name: str,
                                     description: str = "") -> dict:
        """POST /knowledge-bases/ - Create a knowledge base (max 15 per location)."""
        body = self._loc_body({
            "name": name,
            "description": description,
        })
        return await self.request("POST", "/knowledge-bases/", body=body)

    async def get_kb_faqs(self, kb_id: str) -> dict:
        """GET /knowledge-bases/faqs - List FAQs for a knowledge base."""
        return await self.request("GET", "/knowledge-bases/faqs",
                                  query_params=self._loc({"knowledgeBaseId": kb_id}))

    async def create_kb_faq(self, kb_id: str, question: str,
                             answer: str) -> dict:
        """POST /knowledge-bases/faqs - Create a FAQ entry."""
        body = self._loc_body({
            "knowledgeBaseId": kb_id,
            "question": question,
            "answer": answer,
        })
        return await self.request("POST", "/knowledge-bases/faqs", body=body)

    async def update_kb_faq(self, faq_id: str, question: str = "",
                             answer: str = "") -> dict:
        """PUT /knowledge-bases/faqs/{faqId} - Update a FAQ entry."""
        body: dict[str, Any] = {}
        if question:
            body["question"] = question
        if answer:
            body["answer"] = answer
        return await self.request("PUT", f"/knowledge-bases/faqs/{faq_id}",
                                  body=body)

    async def delete_kb_faq(self, faq_id: str) -> dict:
        """DELETE /knowledge-bases/faqs/{faqId} - Delete a FAQ entry."""
        return await self.request("DELETE",
                                  f"/knowledge-bases/faqs/{faq_id}")
