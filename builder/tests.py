"""
builder/tests.py
Automated tests for ResumeCraft AI using SimpleTestCase (Database-Free).
"""

from unittest.mock import patch
from django.test import SimpleTestCase, Client

class ResumeCraftEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_pages_render_successfully(self):
        """Verify all HTML template views return HTTP 200."""
        pages = [
            ('/', 'landing'),
            ('/dashboard/', 'dashboard'),
            ('/create/', 'create_resume'),
            ('/edit/', 'editor'),
            ('/templates/', 'templates'),
            ('/preview/', 'preview'),
        ]
        for url, name in pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Page {url} ({name}) failed")

    def test_sample_resumes_api(self):
        """Verify the static sample resumes API returns valid JSON."""
        response = self.client.get('/api/sample-resumes/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('sample_developer', data.get('data', {}))

    def test_ai_generate_summary_live(self):
        """Test Summary generator endpoint live with Gemini AI."""
        response = self.client.post('/ai/generate-summary/', data={
            'education': 'B.Tech CSE',
            'skills': 'Python, JavaScript',
            'career_goal': 'Backend Engineer'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        if data['success']:
            self.assertTrue(len(data.get('summary', '')) > 0)
        else:
            self.assertTrue(len(data.get('message', '')) > 0)

    def test_ai_improve_experience_live(self):
        """Test Experience Improver endpoint live with Gemini AI."""
        response = self.client.post('/ai/improve-experience/', data={
            'job_title': 'SDE Intern',
            'company': 'Tech Corp',
            'description': 'Built REST endpoints using Django and Python.'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        if data['success']:
            self.assertTrue(len(data.get('improved_text', '')) > 0)
        else:
            self.assertTrue(len(data.get('message', '')) > 0)

    @patch('builder.ai_service.execute_gemini_prompt')
    def test_ai_project_description_endpoint(self, mock_prompt):
        """Test Project description generator endpoint."""
        mock_prompt.return_value = {
            'success': True,
            'text': '• Engineered high-performance backend application.',
            'model': 'gemini-2.5-flash'
        }
        response = self.client.post('/ai/project-description/', data={
            'project_name': 'ResumeCraft AI',
            'technologies': 'Python, Django, Bootstrap',
            'functionality': 'Intelligent resume builder'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('description', data)

    @patch('builder.ai_service.execute_gemini_prompt')
    def test_ai_skill_suggestions_endpoint(self, mock_prompt):
        """Test Skill suggestions endpoint."""
        mock_prompt.return_value = {
            'success': True,
            'text': '{"current_skills": ["Python"], "recommended_to_learn": {"core_technical": ["DSA"]}}',
            'model': 'gemini-2.5-flash'
        }
        response = self.client.post('/ai/skill-suggestions/', data={
            'career_role': 'Software Developer',
            'existing_skills': 'Python, Django'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('data', data)

    @patch('builder.ai_service.execute_gemini_prompt')
    def test_ai_ats_analysis_endpoint(self, mock_prompt):
        """Test ATS analyzer endpoint calculates dynamic score and returns rubric breakdown."""
        mock_prompt.return_value = {
            'success': True,
            'text': '{"actionable_improvements": ["Highlight Python REST frameworks."], "strengths": ["Solid core Python backend foundation."]}',
            'model': 'gemini-2.5-flash'
        }
        response = self.client.post('/ai/ats-analysis/', data={
            'job_description': 'Seeking a Python developer with Django and REST API expertise.',
            'resume_data': {
                'personal': {'fullName': 'Aarav Sharma', 'professionalTitle': 'Python Developer'},
                'skills': {'languages': 'Python', 'frameworks': 'Django, REST API'}
            }
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        score = data.get('data', {}).get('ats_score')
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 40)
        self.assertIn('matching_skills', data.get('data', {}))
        self.assertIn('missing_skills', data.get('data', {}))
        self.assertIn('score_breakdown', data.get('data', {}))
        self.assertIn('explanations', data.get('data', {}))
        self.assertTrue(data.get('data', {}).get('is_indicative', True))

    def test_ai_ats_analysis_empty_job_description(self):
        """Verify ATS analysis requires job description and returns helpful message when missing."""
        response = self.client.post('/ai/ats-analysis/', data={
            'job_description': '   ',
            'resume_data': {'skills': {'languages': 'Python'}}
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data.get('success'))
        self.assertIn('paste a target job description', data.get('message', '').lower())

    def test_ai_ats_analysis_empty_resume(self):
        """Verify ATS analysis detects empty resumes and prompts user to fill resume details."""
        response = self.client.post('/ai/ats-analysis/', data={
            'job_description': 'Looking for a React and Node.js developer.',
            'resume_data': {}
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data.get('success'))
        self.assertIn('empty', data.get('message', '').lower())

    def test_ats_scanner_exact_user_spec(self):
        """
        Verify the exact test case specified by the user:
        Resume skills: React, JavaScript, Node.js, Express.js, MongoDB, REST APIs, Git.
        Job description: Looking for a Full Stack Developer skilled in React, JavaScript, Node.js, MongoDB, Python, Docker and AWS.
        Expected:
        Matched: React, JavaScript, Node.js, MongoDB
        Missing: Python, Docker, AWS
        Do not classify Full Stack Developer as a technical skill.
        Score must not be fixed at 32 or 42.
        """
        from builder.ai_service import calculate_dynamic_ats_score

        resume_data = {
            'personal': {
                'fullName': 'Aarav Sharma',
                'professionalTitle': 'Full Stack Developer',
                'email': 'aarav@example.com',
                'phone': '+91 98765 43210',
                'summary': 'Full stack developer proficient in JavaScript, React, and Node.js.'
            },
            'skills': {
                'languages': 'JavaScript',
                'frameworks': 'React, Node.js, Express.js, REST APIs',
                'tools': 'Git',
                'technical': 'MongoDB'
            },
            'experience': [
                {
                    'company': 'Tech Corp',
                    'role': 'Full Stack Engineer',
                    'description': 'Engineered high-performance web applications using React, Node.js, and MongoDB.'
                }
            ],
            'projects': [
                {
                    'name': 'Cloud Portal',
                    'technologies': 'React, Node.js, Express.js, MongoDB',
                    'description': 'Developed modern responsive portal with RESTful microservices.'
                }
            ],
            'education': [
                {
                    'degree': 'B.Tech in Computer Science',
                    'institution': 'Tech University',
                    'grade': '8.5 CGPA'
                }
            ]
        }

        job_desc = "Looking for a Full Stack Developer skilled in React, JavaScript, Node.js, MongoDB, Python, Docker and AWS."

        res = calculate_dynamic_ats_score(resume_data, job_desc)
        self.assertTrue(res['success'])
        d = res['data']

        matched = d['matching_skills']
        missing = d['missing_skills']
        score = d['ats_score']

        # Expected exact matches: React, JavaScript, Node.js, MongoDB
        self.assertEqual(sorted(matched), sorted(['React', 'JavaScript', 'Node.js', 'MongoDB']))

        # Expected exact missing: Python, Docker, AWS
        self.assertEqual(sorted(missing), sorted(['Python', 'Docker', 'AWS']))

        # Ensure "Full Stack Developer" is not classified as a technical skill
        all_classified = matched + missing
        self.assertNotIn('Full Stack Developer', all_classified)
        self.assertNotIn('Full Stack', all_classified)
        self.assertNotIn('Developer', all_classified)

        # Ensure score is dynamic and not fixed at 32 or 42
        self.assertNotEqual(score, 32)
        self.assertNotEqual(score, 42)
        self.assertGreater(score, 50)
        self.assertLessEqual(score, 100)

        # Check 5-pillar score breakdown is present
        sb = d['score_breakdown']
        self.assertIn('technical_skills', sb)
        self.assertIn('experience_projects', sb)
        self.assertIn('education', sb)
        self.assertIn('competencies', sb)
        self.assertIn('completeness_formatting', sb)

    def test_ats_scanner_synonym_matching(self):
        """Verify equivalent terminology matches properly: JS <=> JavaScript, Postgres <=> PostgreSQL, etc."""
        from builder.ai_service import calculate_dynamic_ats_score

        resume_data = {
            'personal': {'fullName': 'Candidate'},
            'skills': {'languages': 'JS, Postgres, NodeJS'}
        }
        job_desc = "Seeking engineer proficient in JavaScript, PostgreSQL, Node.js."

        res = calculate_dynamic_ats_score(resume_data, job_desc)
        self.assertTrue(res['success'])
        matched = res['data']['matching_skills']

        self.assertIn('JavaScript', matched)
        self.assertIn('PostgreSQL', matched)
        self.assertIn('Node.js', matched)
        self.assertEqual(len(res['data']['missing_skills']), 0)

    def test_ats_scanner_role_title_input(self):
        """Verify that entering a role title like 'backend developer' evaluates against benchmark competencies."""
        from builder.ai_service import calculate_dynamic_ats_score

        resume_data = {
            'personal': {
                'fullName': 'Aarav Sharma',
                'professionalTitle': 'Backend Developer',
                'email': 'aarav@example.com',
                'phone': '+91 98765 43210',
                'summary': 'Backend developer experienced with Python, REST APIs, PostgreSQL, and Git.'
            },
            'skills': {
                'languages': 'Python, SQL',
                'frameworks': 'Django, REST APIs',
                'tools': 'Git, Docker',
                'technical': 'PostgreSQL'
            },
            'experience': [
                {
                    'company': 'Tech Corp',
                    'role': 'Backend Developer',
                    'description': 'Architected REST APIs with Django and PostgreSQL.'
                }
            ],
            'projects': [
                {
                    'name': 'API Gateway',
                    'technologies': 'Python, Docker',
                    'description': 'Engineered high-performance microservices.'
                }
            ],
            'education': [
                {'degree': 'B.Tech in Computer Science', 'institution': 'Tech University'}
            ]
        }

        res = calculate_dynamic_ats_score(resume_data, "backend developer")
        self.assertTrue(res['success'])
        d = res['data']
        self.assertFalse(d.get('no_meaningful_keywords', False))
        self.assertEqual(d.get('target_role'), 'Backend Developer')
        self.assertIn('Python', d.get('matching_skills', []))
        self.assertIn('REST APIs', d.get('matching_skills', []))
        self.assertIn('PostgreSQL', d.get('matching_skills', []))
        self.assertGreater(d.get('ats_score', 0), 60)

    def test_ats_scanner_no_meaningful_keywords_found(self):
        """Verify that when JD has no technical skills, the scanner explains this clearly without generic words."""
        from builder.ai_service import calculate_dynamic_ats_score

        resume_data = {
            'personal': {'fullName': 'Candidate'},
            'skills': {'languages': 'Python, Django'}
        }
        generic_jd = "We are an innovative company looking for energetic and enthusiastic team members with great communication."

        res = calculate_dynamic_ats_score(resume_data, generic_jd)
        self.assertTrue(res['success'])
        d = res['data']
        self.assertTrue(d.get('no_meaningful_keywords'))
        self.assertEqual(len(d.get('matching_skills', [])), 0)
        self.assertEqual(len(d.get('missing_skills', [])), 0)

    def test_calculate_dynamic_ats_score_distinguishes_different_inputs(self):
        """Verify dynamic ATS calculation gives distinctly different scores for matching vs non-matching JDs."""
        from builder.ai_service import calculate_dynamic_ats_score

        sample_resume = {
            'personal': {
                'fullName': 'Aarav Sharma',
                'professionalTitle': 'Full Stack Python Developer',
                'email': 'aarav@example.com',
                'phone': '+91 98765 43210',
                'summary': 'Full stack developer with 2+ years experience in Python, Django, PostgreSQL, and Docker.',
                'github': 'https://github.com/aarav'
            },
            'skills': {
                'languages': 'Python, JavaScript, SQL',
                'frameworks': 'Django, React, REST APIs',
                'tools': 'Docker, Git, PostgreSQL'
            },
            'experience': [
                {
                    'role': 'Backend Developer',
                    'company': 'Tech Corp',
                    'description': 'Engineered high-throughput REST APIs using Django and PostgreSQL. Optimized SQL queries by 35%.'
                }
            ],
            'projects': [
                {
                    'name': 'Cloud Portal',
                    'technologies': 'Python, Django, Docker',
                    'description': 'Architected containerized microservice portal serving 10,000 active users.'
                }
            ],
            'education': [
                {
                    'degree': 'B.Tech in Computer Science and Engineering',
                    'institution': 'Tech University'
                }
            ]
        }

        # Case A: Matching Python/Django Job Description
        python_jd = (
            "We are looking for a Python Software Engineer to build scalable REST APIs with Django and PostgreSQL. "
            "Experience with Docker, Git, and SQL is required. Degree in Computer Science preferred."
        )
        res_matching = calculate_dynamic_ats_score(sample_resume, python_jd)
        score_matching = res_matching['data']['ats_score']

        # Case B: Completely non-matching Java/Cloud architect Job Description
        java_jd = (
            "Seeking a Senior Java Architect with deep expertise in Spring Boot, Kubernetes, AWS, Kafka, Microservices. "
            "Must have extensive experience with Cassandra, Golang, and CI/CD pipelines."
        )
        res_mismatch = calculate_dynamic_ats_score(sample_resume, java_jd)
        score_mismatch = res_mismatch['data']['ats_score']

        # Scores must be dynamic, non-42, and matching must significantly outscore mismatching
        self.assertNotEqual(score_matching, 42)
        self.assertNotEqual(score_mismatch, 42)
        self.assertGreater(score_matching, 75, f"Expected matching score > 75, got {score_matching}")
        self.assertLess(score_mismatch, 55, f"Expected mismatching score < 55, got {score_mismatch}")
        self.assertTrue(score_matching > score_mismatch + 25, "Matching JD must score at least 25 points higher")

        # Verify matched and missing keywords are accurate
        self.assertIn("Python", res_matching['data']['matching_keywords'])
        self.assertIn("Django", res_matching['data']['matching_keywords'])
        self.assertIn("Java", res_mismatch['data']['missing_keywords'])

    @patch('builder.ai_service.execute_gemini_prompt')
    def test_ai_job_match_endpoint(self, mock_prompt):
        """Test Job Match endpoint."""
        mock_prompt.return_value = {
            'success': True,
            'text': '{"match_percentage": 90, "matching_skills": ["Python"]}',
            'model': 'gemini-2.5-flash'
        }
        response = self.client.post('/ai/job-match/', data={
            'job_description': 'Python required.',
            'resume_data': {'skills': {'languages': 'Python'}}
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

    @patch('builder.ai_service.execute_gemini_prompt')
    def test_ai_career_objective_endpoint(self, mock_prompt):
        """Test Career Objective generator endpoint."""
        mock_prompt.return_value = {
            'success': True,
            'text': 'Seeking an entry-level software development role.',
            'model': 'gemini-2.5-flash'
        }
        response = self.client.post('/ai/career-objective/', data={
            'education': 'B.Tech CSE',
            'skills': 'Python',
            'career_interest': 'Software Engineer',
            'experience_level': 'Fresher'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

    @patch('builder.ai_service.execute_gemini_prompt')
    def test_ai_review_resume_endpoint(self, mock_prompt):
        """Test Resume Review diagnostic endpoint."""
        mock_prompt.return_value = {
            'success': True,
            'text': '{"overall_verdict": "Strong profile", "strengths": ["Clean structure"]}',
            'model': 'gemini-2.5-flash'
        }
        response = self.client.post('/ai/review-resume/', data={
            'resume_data': {'title': 'Sample Test', 'personal': {'fullName': 'Aarav'}}
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

    def test_gemini_error_handling(self):
        """Verify that AI failures return meaningful error messages instead of fake success."""
        with patch('builder.ai_service.get_client', return_value=(None, 'gemini-2.5-flash', False)):
            response = self.client.post('/ai/generate-summary/', data={
                'education': 'B.Tech CSE'
            }, content_type='application/json')
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data.get('success'))
            self.assertIn('not configured', data.get('message', '').lower())

    def test_clean_ai_summary_text(self):
        """Verify that summary cleaner strips headings, variations, and conversational intros."""
        from builder.ai_service import clean_ai_summary_text

        raw_sample = (
            "Here are two tailored variations of a professional resume summary:\n\n"
            "**Variation 1: Professional Summary**\n"
            "Passionate Software Engineer with expertise in Python and Django. "
            "Demonstrated track record of architecting scalable applications. "
            "Dedicated to contributing to high-impact development teams.\n\n"
            "**Variation 2: Detailed Overview**\n"
            "• Results-driven technologist with experience..."
        )
        cleaned = clean_ai_summary_text(raw_sample)
        self.assertNotIn("Variation", cleaned)
        self.assertNotIn("Here are", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertIn("Passionate Software Engineer", cleaned)
        self.assertTrue(len(cleaned) > 50)

    def test_clean_ai_bullet_text(self):
        """Verify that bullet cleaner strips intros and trailing notes."""
        from builder.ai_service import clean_ai_bullet_text

        raw_bullets = (
            "Here are 3-4 bullet points for your project:\n"
            "* **Designed a modular architecture** utilizing Django REST framework.\n"
            "* Implemented secure authentication with JWT.\n"
            "- Optimized database queries reducing response time by 40%.\n"
            "*Note: You can add specific traffic metrics.*"
        )
        cleaned = clean_ai_bullet_text(raw_bullets)
        self.assertNotIn("Here are", cleaned)
        self.assertNotIn("Note:", cleaned)
        lines = cleaned.split('\n')
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertTrue(line.startswith("• "))

    @patch('builder.ai_service.execute_gemini_prompt')
    def test_ai_summary_endpoint_cleans_markdown_and_intros(self, mock_prompt):
        """Verify summary endpoint returns clean single-paragraph summary."""
        mock_prompt.return_value = {
            'success': True,
            'text': (
                "Here is your summary:\n\n"
                "**Professional Summary:**\n"
                "Motivated Full Stack Developer proficient in Python, Django, and JavaScript. "
                "Proven ability to build responsive web applications. "
                "Eager to leverage engineering skills in a dynamic software role."
            ),
            'model': 'gemini-2.5-flash'
        }
        response = self.client.post('/ai/generate-summary/', data={
            'education': 'B.Tech CSE',
            'skills': 'Python, Django'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        summary = data.get('summary', '')
        self.assertNotIn("Here is", summary)
        self.assertNotIn("**", summary)
        self.assertNotIn("Professional Summary:", summary)
        self.assertIn("Motivated Full Stack Developer", summary)
