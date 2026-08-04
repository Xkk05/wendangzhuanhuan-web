import os
import tempfile
import unittest
from unittest.mock import Mock

import pymysql

from backend.services.local_processing_record_store import LocalProcessingRecordStore
from backend.services.user_center_service import APP_SCOPE, UserCenterService


class LocalProcessingRecordStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_path = os.path.join(self.temp_dir.name, "processing-records.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def build_store(self):
        return LocalProcessingRecordStore(self.store_path, max_records_per_user=3)

    def append_record(self, store, *, app_user_id="user-1", app_scope="scope-1", file_name="sample.docx"):
        return store.append(
            app_user_id=app_user_id,
            global_user_id=f"global-{app_user_id}",
            app_scope=app_scope,
            tool_name="DOCX To PDF",
            file_name=file_name,
            file_size=128,
            source_format="docx",
            target_format="pdf",
            status="completed",
            result_path="/downloads/sample.pdf",
        )

    def test_records_persist_across_store_instances(self):
        self.append_record(self.build_store())

        records = self.build_store().get_recent(app_user_id="user-1", app_scope="scope-1", limit=10)

        self.assertEqual(1, len(records))
        self.assertEqual("sample.docx", records[0]["fileName"])
        self.assertTrue(records[0]["id"].startswith("local_"))
        self.assertNotIn("appUserId", records[0])

    def test_records_are_isolated_by_user_and_scope(self):
        store = self.build_store()
        self.append_record(store, app_user_id="user-1", app_scope="scope-1", file_name="visible.docx")
        self.append_record(store, app_user_id="user-2", app_scope="scope-1", file_name="other-user.docx")
        self.append_record(store, app_user_id="user-1", app_scope="scope-2", file_name="other-scope.docx")

        records = store.get_recent(app_user_id="user-1", app_scope="scope-1", limit=10)

        self.assertEqual(["visible.docx"], [record["fileName"] for record in records])

    def test_records_are_newest_first_and_pruned_per_user(self):
        store = self.build_store()
        for index in range(4):
            self.append_record(store, file_name=f"file-{index}.docx")

        records = store.get_recent(app_user_id="user-1", app_scope="scope-1", limit=10)

        self.assertEqual(
            ["file-3.docx", "file-2.docx", "file-1.docx"],
            [record["fileName"] for record in records],
        )

    def test_records_can_read_more_than_legacy_twenty_item_limit(self):
        store = LocalProcessingRecordStore(self.store_path, max_records_per_user=25)
        for index in range(25):
            self.append_record(store, file_name=f"file-{index}.docx")

        records = store.get_recent(app_user_id="user-1", app_scope="scope-1", limit=25)
        file_names = [record["fileName"] for record in records]

        self.assertEqual(25, len(records))
        self.assertIn("file-24.docx", file_names)
        self.assertIn("file-0.docx", file_names)

    def test_service_records_local_file_sessions(self):
        service = UserCenterService()
        service._local_processing_records = self.build_store()
        service.get_user_profile = Mock(return_value={
            "user_id": "user-1",
            "global_user_id": "global-user-1",
            "session_source": "local_file",
        })

        service.record_processing(
            "local-token",
            tool_name="DOCX To PDF",
            file_name="converted.docx",
            file_size=256,
            source_format="docx",
            target_format="pdf",
            status="completed",
            result_path="/downloads/converted.pdf",
        )

        records = service.get_recent_records("local-token", limit=10)
        self.assertEqual(["converted.docx"], [record["fileName"] for record in records])

    def test_mysql_write_failure_falls_back_to_local_store(self):
        service = UserCenterService()
        service._local_processing_records = self.build_store()
        service.get_user_profile = Mock(return_value={
            "user_id": "user-1",
            "global_user_id": "global-user-1",
            "session_source": "mysql",
        })
        service.ensure_schema = Mock(side_effect=RuntimeError("database unavailable"))

        service.record_processing(
            "mysql-token",
            tool_name="DOCX To PDF",
            file_name="fallback.docx",
            file_size=512,
            source_format="docx",
            target_format="pdf",
            status="completed",
        )

        records = service._local_processing_records.get_recent(
            app_user_id="user-1",
            app_scope=APP_SCOPE,
            limit=10,
        )
        self.assertEqual(["fallback.docx"], [record["fileName"] for record in records])

    def test_mysql_read_failure_returns_local_records(self):
        service = UserCenterService()
        service._local_processing_records = self.build_store()
        service.get_user_profile = Mock(return_value={
            "user_id": "user-1",
            "global_user_id": "global-user-1",
            "session_source": "mysql",
        })
        service.ensure_schema = Mock(side_effect=pymysql.OperationalError(2003, "database unavailable"))
        self.append_record(
            service._local_processing_records,
            app_user_id="user-1",
            app_scope=APP_SCOPE,
            file_name="read-fallback.docx",
        )

        records = service.get_recent_records("mysql-token", limit=10)

        self.assertEqual(["read-fallback.docx"], [record["fileName"] for record in records])


if __name__ == "__main__":
    unittest.main()
