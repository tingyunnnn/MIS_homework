import unittest
import json
from pathlib import Path

from app import app, tickets, FORM_OPTIONS

EXPECTED_OPTIONS = json.loads(Path(__file__).with_name('expected_options.json').read_text(encoding='utf-8'))


class TicketTests(unittest.TestCase):
    def setUp(self):
        tickets.clear()
        self.client = app.test_client()
        self.payload = {
            "building": "liberal_arts_la", "classroom": "302",
            "equipment": "projector", "description": "cannot_power_on",
            "contact_name": "測試同學", "contact_email": "student+test@example.com",
            "urgency": "一般",
        }

    def tearDown(self):
        tickets.clear()

    def test_create_and_public_privacy(self):
        response = self.client.post('/api/tickets', json=self.payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(tickets[0]['contact_name'], '測試同學')
        self.assertEqual(tickets[0]['contact_email'], self.payload['contact_email'])
        self.assertEqual(tickets[0]['status'], '待審核')
        self.assertEqual(tickets[0]['assignee'], '')
        for ticket in [response.json['ticket'], *self.client.get('/api/tickets').json]:
            self.assertNotIn('contact_name', ticket)
            self.assertNotIn('contact_email', ticket)

    def test_official_option_order_and_unique_values(self):
        for key, count in [('buildings', 21), ('equipment', 6), ('description', 5)]:
            options = FORM_OPTIONS[key]
            self.assertEqual([list(option) for option in options], EXPECTED_OPTIONS[key])
            self.assertEqual(len(options), count)
            self.assertEqual(len({value for value, label in options}), count)

    def test_all_official_buildings(self):
        for value, label in EXPECTED_OPTIONS['buildings']:
            with self.subTest(building=value):
                response = self.client.post('/api/tickets', json={**self.payload, 'building': value})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json['ticket']['building'], value)
                self.assertEqual(response.json['ticket']['location'], f'{label} 302')

    def test_all_official_equipment(self):
        for value, label in EXPECTED_OPTIONS['equipment']:
            with self.subTest(equipment=value):
                response = self.client.post('/api/tickets', json={**self.payload, 'equipment': value, 'equipment_other': '自訂設備'})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json['ticket']['equipment_type'], value)
                self.assertEqual(response.json['ticket']['equipment'], '自訂設備' if value == 'other' else label)

    def test_all_official_descriptions(self):
        for value, label in EXPECTED_OPTIONS['description']:
            with self.subTest(description=value):
                response = self.client.post('/api/tickets', json={**self.payload, 'description': value, 'description_other': '自訂問題'})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json['ticket']['description_type'], value)
                self.assertEqual(response.json['ticket']['description'], '自訂問題' if value == 'other' else label)

    def test_old_option_values_rejected(self):
        for field, value in [('building', 'test_building'), ('equipment', 'test_equipment'),
                             ('description', 'test_problem'), ('building', 'IL'), ('building', 'LA')]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.client.post('/api/tickets', json={**self.payload, field: value}).status_code, 400)
        self.assertEqual(tickets, [])

    def test_required_fields_and_types(self):
        for field in self.payload:
            for invalid in ['', '   ', None, [], 123]:
                with self.subTest(field=field, invalid=invalid):
                    response = self.client.post('/api/tickets', json={**self.payload, field: invalid})
                    self.assertEqual(response.status_code, 400)
                    self.assertTrue(response.json['message'])
        self.assertEqual(tickets, [])

    def test_email(self):
        for email in ['wrong', 'a@', 'a@localhost', 'a b@example.com', 'a@-example.com']:
            with self.subTest(email=email):
                self.assertEqual(self.client.post('/api/tickets', json={**self.payload, 'contact_email': email}).status_code, 400)
        for email in ['name@example.org', 'first.last+tag@sub.example.com']:
            self.assertEqual(self.client.post('/api/tickets', json={**self.payload, 'contact_email': email}).status_code, 201)

    def test_other_required_and_saved(self):
        for field in ['equipment', 'description']:
            for invalid in ['', '   ', None, []]:
                with self.subTest(field=field, invalid=invalid):
                    response = self.client.post('/api/tickets', json={**self.payload, field: 'other', f'{field}_other': invalid})
                    self.assertEqual(response.status_code, 400)
            response = self.client.post('/api/tickets', json={**self.payload, field: 'other', f'{field}_other': ' 自訂內容 '})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json['ticket'][field], '自訂內容')

    def test_unrelated_custom_content_ignored(self):
        response = self.client.post('/api/tickets', json={**self.payload, 'equipment_other': '無關設備', 'description_other': '無關問題'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(tickets[0]['equipment_other'], '')
        self.assertEqual(tickets[0]['description_other'], '')

    def test_invalid_options_and_json(self):
        for field in ['building', 'equipment', 'description', 'urgency']:
            self.assertEqual(self.client.post('/api/tickets', json={**self.payload, field: '不存在'}).status_code, 400)
        for invalid in [[], 'text', 123]:
            self.assertEqual(self.client.post('/api/tickets', json=invalid).status_code, 400)
        self.assertEqual(self.client.post('/api/tickets', data='{', content_type='application/json').status_code, 400)

    def test_urgency_and_admin_status(self):
        for urgency in ['一般', '急件', '緊急']:
            response = self.client.post('/api/tickets', json={**self.payload, 'urgency': urgency})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json['ticket']['urgency'], urgency)
        for status in ['待審核', '已派工', '處理中', '等待零件', '已結案']:
            response = self.client.patch('/api/tickets/T-001', json={'status': status, 'assignee': '測試技師'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['ticket']['status'], status)
            self.assertNotIn('contact_email', response.json['ticket'])
        self.assertEqual(self.client.patch('/api/tickets/T-001', json={'status': '已完成'}).status_code, 400)
        self.assertEqual(self.client.patch('/api/tickets/missing', json={'status': '處理中'}).status_code, 404)

    def test_pages(self):
        for path in ['/', '/admin']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('<th>聯絡方式</th>', response.get_data(as_text=True))
            self.assertNotIn('MIS 前後端範例', response.get_data(as_text=True))

    def test_old_waiting_status_rejected(self):
        self.client.post('/api/tickets', json=self.payload)
        original = tickets[0].copy()
        response = self.client.patch('/api/tickets/T-001', json={'status': '待料中', 'assignee': '技師'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(tickets[0], original)

    def test_unprotected_backend_contact_api(self):
        self.assertEqual(self.client.get('/api/admin/tickets').json, [])
        self.client.post('/api/tickets', json=self.payload)
        self.client.patch('/api/tickets/T-001', json={'status': '等待零件', 'assignee': '虛構技師'})
        response = self.client.get('/api/admin/tickets')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json[0]['contact_name'], self.payload['contact_name'])
        self.assertEqual(response.json[0]['contact_email'], self.payload['contact_email'])
        self.assertEqual(response.json[0]['status'], '等待零件')
        for ticket in self.client.get('/api/tickets').json:
            self.assertNotIn('contact_name', ticket)
            self.assertNotIn('contact_email', ticket)

    def test_pending_without_assignee(self):
        self.client.post('/api/tickets', json=self.payload)
        for payload in [{'status': '待審核'}, {'status': '待審核', 'assignee': ''},
                        {'status': '待審核', 'assignee': '   '}]:
            self.assertEqual(self.client.patch('/api/tickets/T-001', json=payload).status_code, 200)
            self.assertEqual(tickets[0]['assignee'], '')

    def test_assignee_required_and_atomic_failure(self):
        from copy import deepcopy
        self.client.post('/api/tickets', json=self.payload)
        original = deepcopy(tickets[0])
        for status in ['已派工', '處理中', '等待零件', '已結案']:
            for value in ['', '   ', None, [], 123]:
                with self.subTest(status=status, value=value):
                    response = self.client.patch('/api/tickets/T-001', json={'status': status, 'assignee': value})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('負責人', response.json['message'])
                    self.assertEqual(tickets[0], original)
            self.assertEqual(self.client.patch('/api/tickets/T-001', json={'status': status}).status_code, 400)
            self.assertEqual(tickets[0], original)

    def test_update_both_and_free_transitions(self):
        self.client.post('/api/tickets', json=self.payload)
        for status in ['已結案', '已派工', '等待零件', '處理中', '待審核']:
            response = self.client.patch('/api/tickets/T-001', json={'status': status, 'assignee': ' 王技師 '})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['ticket']['status'], status)
            self.assertEqual(response.json['ticket']['assignee'], '王技師')
            self.assertNotIn('contact_name', response.json['ticket'])
            self.assertNotIn('contact_email', response.json['ticket'])
        # 省略 assignee 保留原值，空字串則清除。
        self.assertEqual(self.client.patch('/api/tickets/T-001', json={'status': '已派工'}).status_code, 200)
        self.assertEqual(tickets[0]['assignee'], '王技師')
        self.assertEqual(self.client.patch('/api/tickets/T-001', json={'status': '待審核', 'assignee': ''}).status_code, 200)
        self.assertEqual(self.client.get('/api/tickets').json[0]['assignee'], '')

    def test_invalid_update_preserves_existing_assignment(self):
        from copy import deepcopy
        self.client.post('/api/tickets', json=self.payload)
        self.client.patch('/api/tickets/T-001', json={'status': '處理中', 'assignee': '原技師'})
        original = deepcopy(tickets[0])
        for payload in [{'status': '錯誤', 'assignee': '新技師'},
                        {'status': '已結案', 'assignee': ' '},
                        {'status': None, 'assignee': '新技師'},
                        {'status': '待審核', 'assignee': None}, [], 'text']:
            self.assertEqual(self.client.patch('/api/tickets/T-001', json=payload).status_code, 400)
            self.assertEqual(tickets[0], original)


if __name__ == '__main__':
    unittest.main()
