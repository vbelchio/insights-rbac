#
# Copyright 2024 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Test the Audit Logs Model."""
from django.db import transaction
from django.test import TestCase
from unittest.mock import Mock
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from management.models import Workspace
from tests.identity_request import IdentityRequest


class WorkspaceViewTests(IdentityRequest):
    """Test the Workspace Model."""

    def setUp(self):
        """Set up the audit log model tests."""
        super().setUp()
        self.parent_workspace = Workspace.objects.create(name="Parent Workspace", tenant=self.tenant)
        self.init_workspace = Workspace.objects.create(
            name="Init Workspace",
            description="Init Workspace - description",
            tenant=self.tenant,
            parent=self.parent_workspace,
        )

    def tearDown(self):
        """Tear down group model tests."""
        Workspace.objects.update(parent=None)
        Workspace.objects.all().delete()

    def test_create_workspace(self):
        """Test for creating a workspace."""
        workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": "cbe9822d-cadb-447d-bc80-8bef773c36ea",
        }

        parent_workspace = Workspace.objects.create(**workspace_data)
        workspace = {"name": "New Workspace", "description": "Workspace", "parent_id": parent_workspace.uuid}

        url = reverse("workspace-list")
        client = APIClient()
        response = client.post(url, workspace, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data.get("name"), "New Workspace")
        self.assertNotEquals(data.get("uuid"), "")
        self.assertIsNotNone(data.get("uuid"))
        self.assertNotEquals(data.get("created"), "")
        self.assertNotEquals(data.get("modified"), "")
        self.assertEquals(data.get("description"), "Workspace")
        self.assertEqual(response.get("content-type"), "application/json")

    def test_create_workspace_without_parent(self):
        """Test for creating a workspace."""
        workspace = {"name": "New Workspace", "description": "Workspace"}

        url = reverse("workspace-list")
        client = APIClient()
        response = client.post(url, workspace, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data.get("name"), "New Workspace")
        self.assertNotEquals(data.get("uuid"), "")
        self.assertIsNotNone(data.get("uuid"))
        self.assertNotEquals(data.get("created"), "")
        self.assertNotEquals(data.get("modified"), "")
        self.assertEquals(data.get("description"), "Workspace")
        self.assertEqual(response.get("content-type"), "application/json")

    def test_create_workspace_empty_body(self):
        """Test for creating a workspace."""
        workspace = {}

        url = reverse("workspace-list")
        client = APIClient()
        response = client.post(url, workspace, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        self.assertIsNotNone(detail)
        self.assertEqual(detail, "Field 'name' is required.")

        self.assertEqual(status_code, 400)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_create_workspace_unauthorized(self):
        """Test for creating a workspace."""
        workspace = {}

        request_context = self._create_request_context(self.customer_data, self.user_data, is_org_admin=False)

        request = request_context["request"]
        headers = request.META

        url = reverse("workspace-list")
        client = APIClient()
        response = client.post(url, workspace, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        self.assertEqual(detail, "You do not have permission to perform this action.")
        self.assertEqual(status_code, 403)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_duplicate_create_workspace(self):
        """Test that creating a duplicate workspace is allowed."""
        workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": self.init_workspace.uuid,
        }

        Workspace.objects.create(**workspace_data)

        test_data = {"name": "New Workspace", "parent_id": self.init_workspace.uuid}

        url = reverse("workspace-list")
        client = APIClient()
        response = client.post(url, test_data, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.get("content-type"), "application/json")

    def test_update_workspace(self):
        """Test for updating a workspace."""
        workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": self.init_workspace.uuid,
        }

        workspace = Workspace.objects.create(**workspace_data)

        url = reverse("workspace-detail", kwargs={"uuid": workspace.uuid})
        client = APIClient()

        workspace_data["name"] = "Updated name"
        workspace_data["description"] = "Updated description"
        workspace_data["parent_id"] = workspace.parent_id
        response = client.put(url, workspace_data, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data.get("name"), "Updated name")
        self.assertNotEquals(data.get("uuid"), "")
        self.assertIsNotNone(data.get("uuid"))
        self.assertNotEquals(data.get("created"), "")
        self.assertNotEquals(data.get("modified"), "")
        self.assertEquals(data.get("description"), "Updated description")

        update_workspace = Workspace.objects.filter(id=workspace.id).first()
        self.assertEquals(update_workspace.name, "Updated name")
        self.assertEquals(update_workspace.description, "Updated description")
        self.assertEqual(response.get("content-type"), "application/json")

    def test_partial_update_workspace_with_put_method(self):
        """Test for updating a workspace."""
        workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": "cbe9822d-cadb-447d-bc80-8bef773c36ea",
        }

        workspace = Workspace.objects.create(**workspace_data)

        url = reverse("workspace-detail", kwargs={"uuid": workspace.uuid})
        client = APIClient()

        workspace_request_data = {"name": "New Workspace"}

        response = client.put(url, workspace_request_data, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        instance = response.data.get("instance")
        self.assertIsNotNone(detail)
        self.assertEqual(detail, "Field 'description' is required.")
        self.assertEqual(status_code, 400)
        self.assertEqual(instance, url)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_update_workspace_same_parent(self):
        """Test for updating a workspace."""
        parent_workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": "cbe9822d-cadb-447d-bc80-8bef773c36ea",
        }

        parent_workspace = Workspace.objects.create(**parent_workspace_data)

        workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": parent_workspace.uuid,
        }

        workspace = Workspace.objects.create(**workspace_data)

        url = reverse("workspace-detail", kwargs={"uuid": workspace.uuid})
        client = APIClient()

        workspace_request_data = {"name": "New Workspace", "parent_id": workspace.uuid, "description": "XX"}

        response = client.put(url, workspace_request_data, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        self.assertIsNotNone(detail)
        self.assertEqual(detail, "Parent ID and UUID can't be same")
        self.assertEqual(status_code, 400)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_update_workspace_parent_doesnt_exist(self):
        """Test for updating a workspace."""

        workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
        }

        workspace = Workspace.objects.create(**workspace_data)

        url = reverse("workspace-detail", kwargs={"uuid": workspace.uuid})
        client = APIClient()

        parent = "cbe9822d-cadb-447d-bc80-8bef773c36ea"
        workspace_request_data = {
            "name": "New Workspace",
            "parent_id": parent,
            "description": "XX",
        }

        response = client.put(url, workspace_request_data, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        instance = response.data.get("instance")
        self.assertIsNotNone(detail)
        self.assertEqual(detail, f"Parent workspace '{parent}' doesn't exist in tenant")
        self.assertEqual(status_code, 400)
        self.assertEqual(instance, url)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_partial_update_workspace(self):
        """Test for updating a workspace."""
        workspace_data = {
            "name": "New Workspace",
            "description": "New Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": None,
        }

        workspace = Workspace.objects.create(**workspace_data)

        url = reverse("workspace-detail", kwargs={"uuid": workspace.uuid})
        client = APIClient()

        workspace_data = {"name": "Updated name"}
        response = client.patch(url, workspace_data, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data.get("name"), "Updated name")
        self.assertNotEquals(data.get("uuid"), "")
        self.assertIsNotNone(data.get("uuid"))
        self.assertNotEquals(data.get("created"), "")
        self.assertNotEquals(data.get("modified"), "")

        update_workspace = Workspace.objects.filter(id=workspace.id).first()
        self.assertEquals(update_workspace.name, "Updated name")
        self.assertEqual(response.get("content-type"), "application/json")

    def test_update_workspace_empty_body(self):
        """Test for updating a workspace with empty body"""
        workspace = {}

        url = reverse("workspace-detail", kwargs={"uuid": self.init_workspace.uuid})
        client = APIClient()
        response = client.put(url, workspace, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        instance = response.data.get("instance")
        self.assertIsNotNone(detail)
        self.assertEqual(detail, "Field 'name' is required.")
        self.assertEqual(status_code, 400)
        self.assertEqual(instance, url)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_update_duplicate_workspace(self):
        workspace_data = {
            "name": "New Duplicate Workspace",
            "description": "New Duplicate Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": self.init_workspace.uuid,
        }

        Workspace.objects.create(**workspace_data)

        workspace_data_for_update = {
            "name": "New Duplicate Workspace for Update",
            "description": "New Duplicate Workspace - description",
            "tenant_id": self.tenant.id,
            "parent_id": self.init_workspace.uuid,
        }

        workspace_for_update = Workspace.objects.create(**workspace_data_for_update)

        url = reverse("workspace-detail", kwargs={"uuid": workspace_for_update.uuid})
        client = APIClient()

        workspace_data_for_put = {
            "name": "New Duplicate Workspace",
            "description": "New Duplicate Workspace - description",
            "parent_id": self.init_workspace.uuid,
        }

        response = client.put(url, workspace_data_for_put, format="json", **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get("content-type"), "application/json")

    def test_update_workspace_unauthorized(self):
        workspace = {}

        request_context = self._create_request_context(self.customer_data, self.user_data, is_org_admin=False)

        request = request_context["request"]
        headers = request.META

        url = reverse("workspace-detail", kwargs={"uuid": self.init_workspace.uuid})
        client = APIClient()
        response = client.put(url, workspace, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        status_code = response.data.get("status")
        detail = response.data.get("detail")

        self.assertEqual(detail, "You do not have permission to perform this action.")
        self.assertEqual(status_code, 403)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_get_workspace(self):
        url = reverse("workspace-detail", kwargs={"uuid": self.init_workspace.uuid})
        client = APIClient()
        response = client.get(url, None, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data.get("name"), "Init Workspace")
        self.assertEquals(data.get("description"), "Init Workspace - description")
        self.assertNotEquals(data.get("uuid"), "")
        self.assertIsNotNone(data.get("uuid"))
        self.assertNotEquals(data.get("created"), "")
        self.assertNotEquals(data.get("modified"), "")
        self.assertEqual(response.get("content-type"), "application/json")
        self.assertEqual(data.get("ancestry"), None)
        self.assertEqual(response.get("content-type"), "application/json")

    def test_get_workspace_with_ancestry(self):
        base_url = reverse("workspace-detail", kwargs={"uuid": self.init_workspace.uuid})
        url = f"{base_url}?include_ancestry=true"
        client = APIClient()
        response = client.get(url, None, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data.get("name"), "Init Workspace")
        self.assertEquals(data.get("description"), "Init Workspace - description")
        self.assertNotEquals(data.get("uuid"), "")
        self.assertIsNotNone(data.get("uuid"))
        self.assertNotEquals(data.get("created"), "")
        self.assertNotEquals(data.get("modified"), "")
        self.assertEqual(
            data.get("ancestry"),
            [{"name": self.parent_workspace.name, "uuid": str(self.parent_workspace.uuid), "parent_id": None}],
        )
        self.assertEqual(response.get("content-type"), "application/json")
        self.assertEqual(data.get("ancestry"), None)

    def test_get_workspace_with_ancestry(self):
        base_url = reverse("workspace-detail", kwargs={"uuid": self.init_workspace.uuid})
        url = f"{base_url}?include_ancestry=true"
        client = APIClient()
        response = client.get(url, None, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data.get("name"), "Init Workspace")
        self.assertEquals(data.get("description"), "Init Workspace - description")
        self.assertNotEquals(data.get("uuid"), "")
        self.assertIsNotNone(data.get("uuid"))
        self.assertNotEquals(data.get("created"), "")
        self.assertNotEquals(data.get("modified"), "")
        self.assertEqual(
            data.get("ancestry"),
            [{"name": self.parent_workspace.name, "uuid": str(self.parent_workspace.uuid), "parent_id": None}],
        )
        self.assertEqual(response.get("content-type"), "application/json")

    def test_get_workspace_not_found(self):
        url = reverse("workspace-detail", kwargs={"uuid": "XXXX"})
        client = APIClient()
        response = client.get(url, None, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        status_code = response.data.get("status")
        detail = response.data.get("detail")

        self.assertEqual(detail, "Not found.")
        self.assertEqual(status_code, 404)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_get_workspace_unauthorized(self):
        request_context = self._create_request_context(self.customer_data, self.user_data, is_org_admin=False)

        request = request_context["request"]
        headers = request.META

        url = reverse("workspace-detail", kwargs={"uuid": self.init_workspace.uuid})
        client = APIClient()
        response = client.get(url, None, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        status_code = response.data.get("status")
        detail = response.data.get("detail")

        self.assertEqual(detail, "You do not have permission to perform this action.")
        self.assertEqual(status_code, 403)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_delete_workspace(self):
        workspace_data = {
            "name": "Workspace for delete",
            "description": "Workspace for delete - description",
            "tenant_id": self.tenant.id,
        }

        workspace = Workspace.objects.create(**workspace_data)

        url = reverse("workspace-detail", kwargs={"uuid": workspace.uuid})
        client = APIClient()
        test_headers = self.headers.copy()
        test_headers["HTTP_ACCEPT"] = "application/problem+json"
        response = client.delete(url, None, format="json", **test_headers)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.headers.get("content-type"), None)
        deleted_workspace = Workspace.objects.filter(id=workspace.id).first()
        self.assertIsNone(deleted_workspace)

    def test_delete_workspace_not_found(self):
        url = reverse("workspace-detail", kwargs={"uuid": "XXXX"})
        client = APIClient()
        response = client.delete(url, None, format="json", **self.headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        self.assertEqual(detail, "Not found.")
        self.assertEqual(status_code, 404)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_delete_workspace_unauthorized(self):
        request_context = self._create_request_context(self.customer_data, self.user_data, is_org_admin=False)

        request = request_context["request"]
        headers = request.META

        url = reverse("workspace-detail", kwargs={"uuid": self.init_workspace.uuid})
        client = APIClient()
        response = client.delete(url, None, format="json", **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        status_code = response.data.get("status")
        detail = response.data.get("detail")
        self.assertEqual(detail, "You do not have permission to perform this action.")
        self.assertEqual(status_code, 403)
        self.assertEqual(response.get("content-type"), "application/problem+json")

    def test_get_workspace_list(self):
        """Test for listing workspaces."""
        url = reverse("workspace-list")
        client = APIClient()
        response = client.get(url, None, format="json", **self.headers)

        payload = response.data
        self.assertIsInstance(payload.get("data"), list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get("content-type"), "application/json")
        self.assertEqual(payload.get("meta").get("count"), Workspace.objects.count())
        for keyname in ["meta", "links", "data"]:
            self.assertIn(keyname, payload)
        for keyname in ["name", "uuid", "parent_id", "description"]:
            self.assertIn(keyname, payload.get("data")[0])
