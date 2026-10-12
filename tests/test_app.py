import unittest

from app import app, tickets


class TicketTests(unittest.TestCase):
    def setUp(self):
        tickets.clear()
        self.client = app.test_client()
        self.payload = {
            "building": "test_building", "classroom": "302",
            "equipment": "test_equipment", "description": "test_problem",
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
        self.assertEqual(tickets[0]['status'], '待處理')
        for ticket in [response.json['ticket'], *self.client.get('/api/tickets').json]:
            self.assertNotIn('contact_name', ticket)
            self.assertNotIn('contact_email', ticket)

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
        for status in ['待處理', '處理中', '已完成']:
            response = self.client.patch('/api/tickets/T-001', json={'status': status})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['ticket']['status'], status)
            self.assertNotIn('contact_email', response.json['ticket'])
        self.assertEqual(self.client.patch('/api/tickets/T-001', json={'status': '已派工'}).status_code, 400)
        self.assertEqual(self.client.patch('/api/tickets/missing', json={'status': '處理中'}).status_code, 404)

    def test_pages(self):
        for path in ['/', '/admin']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('<th>聯絡方式</th>', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
