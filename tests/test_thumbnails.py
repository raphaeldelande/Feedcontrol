import io
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont
import ai_server as app
from thumbnail_analysis import ThumbnailAnalyzer

class ThumbnailTests(unittest.TestCase):
    def picture(self, kind):
        image=Image.new('RGB',(320,180),'#dddddd')
        draw=ImageDraw.Draw(image)
        if kind=='circle':draw.ellipse((70,35,190,150),outline='#ff0000',width=8)
        if kind=='arrow':draw.polygon([(40,75),(160,75),(160,40),(240,90),(160,140),(160,105),(40,105)],fill='#ff0000')
        if kind=='shirt':draw.rectangle((70,35,190,150),fill='#ff0000')
        return image

    def test_red_circle_arrow_and_red_object(self):
        for kind,key in [('circle','redCircleLikeCount'),('arrow','redArrowLikeCount')]:
            with self.subTest(kind=kind):
                signals=ThumbnailAnalyzer.pixels(self.picture(kind))
                self.assertGreaterEqual(signals[key],1)
        shirt=ThumbnailAnalyzer.pixels(self.picture('shirt'))
        self.assertEqual(shirt['redCircleLikeCount'],0)
        self.assertEqual(shirt['redArrowLikeCount'],0)

    def test_monochrome_alone_not_motivation(self):
        image=self.picture('plain')
        signals=ThumbnailAnalyzer.pixels(image)
        self.assertTrue(signals['monochrome'])
        with patch.object(app.thumbnail_analyzer,'analyze',return_value={'status':'analyzed','signals':signals,'ocrText':'','learned':None}):
            v=app.classify({'title':'Une image du jour','videoId':'abcdefghijk','analyzeThumbnail':True})
        self.assertEqual(v['topics'],[])
        self.assertTrue(v['thumbnailAnalyzed'])
        self.assertLess(v['qualityConfidence'],.5)

    def test_actual_ocr_motivational_text(self):
        analyzer=ThumbnailAnalyzer()
        if not analyzer.ocr_command:self.skipTest('Tesseract absent : test OCR non exécuté')
        image=Image.new('RGB',(640,360),'black')
        try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',52)
        except OSError:font=ImageFont.load_default(size=48)
        ImageDraw.Draw(image).text((35,130),'FOCUS IN LIFE',fill='white',font=font)
        buf=io.BytesIO();image.save(buf,format='PNG')
        actual=analyzer.analyze_bytes(buf.getvalue())
        self.assertIn('FOCUS',actual['ocrText'].upper())
        with patch.object(app.thumbnail_analyzer,'analyze',return_value=actual):
            v=app.classify({'title':'Episode 12','videoId':'abcdefghijk','analyzeThumbnail':True})
        self.assertIn('motivation',v['topics'])
        self.assertTrue(v['thumbnailAnalyzed'])
        self.assertEqual(v['qualityConfidence'],.15)

    def test_fetch_cache_validation_and_failure(self):
        buf=io.BytesIO();self.picture('circle').save(buf,format='PNG');calls=[]
        def fetch(video_id):calls.append(video_id);return buf.getvalue()
        analyzer=ThumbnailAnalyzer(fetch);analyzer.ocr_command=None
        self.assertEqual(analyzer.analyze('abcdefghijk')['status'],'analyzed')
        self.assertEqual(analyzer.analyze('abcdefghijk')['status'],'analyzed')
        self.assertEqual(len(calls),1)
        self.assertEqual(analyzer.analyze('../../localhost')['status'],'unavailable')
        self.assertEqual(len(calls),1)
        def fail(_):raise TimeoutError()
        self.assertEqual(ThumbnailAnalyzer(fail).analyze('abcdefghijk')['status'],'unavailable')

    def test_visual_model_failure_stays_explicit(self):
        analyzer=ThumbnailAnalyzer();analyzer.model_ready=True;analyzer.model='nonexistent-test-model'
        with patch('thumbnail_analysis.urlopen',side_effect=TimeoutError()):
            self.assertIsNone(analyzer.learned(self.picture('plain')))

if __name__=='__main__':unittest.main()
