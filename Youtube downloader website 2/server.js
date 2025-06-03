const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { exec } = require('yt-dlp-exec');
const { PassThrough } = require('stream');
const fs = require('fs');
const https = require('https');
const { spawn } = require('child_process');

const app = express();
const PORT = 3000;

process.on('uncaughtException', (err) => {
  console.error('[FATAL] Uncaught Exception:', err);
});
process.on('unhandledRejection', (reason, promise) => {
  console.error('[FATAL] Unhandled Rejection:', reason);
});

app.use(helmet());
app.use(cors({
  origin: [
    'https://downloader.groupxyz.me',
    'http://downloader.groupxyz.me',
    'https://groupxyz.me',
    'http://groupxyz.me',
    'http://localhost:3000',
    'http://localhost:8080',
    'http://127.0.0.1:3000'
  ],
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json());
app.use(rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10, 
  message: 'Too many requests, please try again later.'
}));

app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

function sanitizeFilename(name) {
  return name.replace(/[^a-z0-9_\-\.]/gi, '_').substring(0, 80);
}

app.post('/api/download', async (req, res) => {
  try {
    const { url, quality } = req.body;
    if (
      typeof url !== 'string' ||
      !/^https?:\/\//.test(url)
    ) {
      console.error('Invalid URL:', url);
      return res.status(400).json({ error: 'Invalid URL.' });
    }

    if (url.includes('spotify.com')) {
      let spotUrl = url.replace(/\/intl-[a-z]{2}(?:-[A-Z]{2,3})?\//g, '/');
      spotUrl = spotUrl.split('?')[0];
      const spotdl = spawn('spotdl', [spotUrl, '--output', '-', '--format', 'mp3'], { stdio: ['ignore', 'pipe', 'pipe'] });
      let chunks = [];
      let errorOutput = '';
      let responded = false;
      spotdl.stdout.on('data', (data) => {
        chunks.push(data);
      });
      spotdl.stderr.on('data', (data) => {
        errorOutput += data.toString();
        console.error(`[spotDL] ${data}`);
      });
      spotdl.on('error', (err) => {
        console.error('spotDL error:', err);
        if (!responded) {
          responded = true;
          res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
          res.setHeader('Content-Type', 'text/plain');
          res.end('Error during Spotify download.\n' + (err.message || ''));
        }
      });
      spotdl.on('close', (code) => {
        if (responded) return;
        responded = true;
        if (code !== 0) {
          const log = errorOutput || Buffer.concat(chunks).toString() || 'Unknown error';
          res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
          res.setHeader('Content-Type', 'text/plain');
          res.end('Spotify download failed!\n' + log);
          return;
        }
        const buffer = Buffer.concat(chunks);
        const isMp3 = buffer.slice(0, 3).toString() === 'ID3' || (buffer[0] === 0xFF && (buffer[1] & 0xE0) === 0xE0);
        if (!isMp3) {
          const log = errorOutput + '\n' + buffer.toString();
          res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
          res.setHeader('Content-Type', 'text/plain');
          res.end('Spotify did not return a valid MP3 file!\n' + log);
          return;
        }
        const filename = 'spotify_track.mp3';
        res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
        res.setHeader('Content-Type', 'audio/mpeg');
        res.end(buffer);
      });
      return;
    }

    const info = await exec(url, {
      dumpSingleJson: true,
      noWarnings: true,
      noCheckCertificate: true,
      preferFreeFormats: true,
      youtubeSkipDashManifest: true
    });

    const availableFormat = (info.formats || []).find(f => f.format_id === quality || f.ext === quality || f.format_note === quality || f.quality_label === quality);
    if (!availableFormat && !quality.includes('mp3') && !quality.includes('m4a')) {
      return res.status(400).json({ error: 'Requested format is not available. Try another format.' });
    }

    const title = sanitizeFilename(info.title || 'download_groupxyz.me');
    const ext = quality.includes('mp3') ? 'mp3' : quality.includes('m4a') ? 'm4a' : 'mp4';
    const filename = `${title}.${ext}`;

    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Type', 'application/octet-stream');

    const ytdlp = exec(url, {
      output: '-',
      format: quality,
      audioFormat: ext === 'mp3' ? 'mp3' : undefined,
      audioQuality: '0',
      noCheckCertificate: true,
      noWarnings: true,
      preferFreeFormats: true,
      youtubeSkipDashManifest: true,
    }, { stdio: ['ignore', 'pipe', 'pipe'] });

    ytdlp.stdout.pipe(res);
    ytdlp.stderr.on('data', (data) => {
      console.error(`[yt-dlp] ${data}`);
    });
    ytdlp.on('error', (err) => {
      console.error('yt-dlp error:', err);
      res.status(500).end('Error during download.');
    });
    ytdlp.on('close', (code) => {
      if (code !== 0) {
        console.error('yt-dlp exited with code', code);
        res.status(500).end('Error during download.');
      }
    });
  } catch (err) {
    console.error('Download-Handler Exception:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});

app.post('/api/info', async (req, res) => {
  try {
    const { url } = req.body;
    if (
      typeof url !== 'string' ||
      !/^https?:\/\//.test(url)
    ) {
      console.error('Invalid URL:', url);
      return res.status(400).json({ error: 'Invalid URL.' });
    }
    if (url.includes('spotify.com')) {
      let spotUrl = url.replace(/\/intl-[a-z]{2}(?:-[A-Z]{2,3})?\//g, '/');
      spotUrl = spotUrl.split('?')[0];
      const spotdl = spawn('spotdl', ['meta', spotUrl, '--output', 'json']);
      let output = '';
      let errorOutput = '';
      let responded = false;
      spotdl.stdout.on('data', (data) => {
        output += data.toString();
      });
      spotdl.stderr.on('data', (data) => {
        errorOutput += data.toString();
      });
      spotdl.on('error', (err) => {
        console.error('spotDL meta error:', err);
        if (!responded) {
          responded = true;
          if (err.code === 'ENOENT') {
            return res.status(500).json({ error: 'spotDL is not installed or not in PATH. Please install spotDL (pip install spotdl).' });
          }
          return res.status(500).json({ error: 'Failed to get Spotify metadata.' });
        }
      });
      spotdl.on('close', (code) => {
        if (responded) return;
        responded = true;
        if (code !== 0) {
          console.error('spotDL meta exited with code', code, errorOutput);
          return res.status(500).json({ error: 'Failed to get Spotify metadata. ' + errorOutput.trim() });
        }
        try {
          if (!output.trim().startsWith('{') && !output.trim().startsWith('[')) {
            console.error('spotDL did not return JSON:', output.trim());
            return res.status(500).json({ error: 'spotDL did not return valid metadata. ' + output.trim() });
          }
          const meta = JSON.parse(output);
          const track = Array.isArray(meta) ? meta[0] : meta;
          res.json({
            title: track.title || 'Spotify Track',
            uploader: track.artists ? track.artists.join(', ') : 'Spotify',
            duration: track.duration ? new Date(track.duration * 1000).toISOString().substr(11, 8) : '',
            views: '',
            thumbnail: track.cover_url || '',
            formats: [
              { quality: 'MP3', ext: 'mp3', size: '', format_id: 'mp3' }
            ]
          });
        } catch (e) {
          console.error('Failed to parse spotDL metadata:', e, output);
          res.status(500).json({ error: 'Could not parse Spotify metadata. ' + output.trim() });
        }
      });
      return;
    }
    const info = await exec(url, {
      dumpSingleJson: true,
      noWarnings: true,
      noCheckCertificate: true,
      preferFreeFormats: true,
      youtubeSkipDashManifest: true
    });
    res.json({
      title: info.title || 'Unknown Title',
      uploader: info.uploader || info.artist || info.channel || 'Unknown',
      duration: info.duration ? new Date(info.duration * 1000).toISOString().substr(11, 8) : '',
      views: info.view_count ? info.view_count.toLocaleString() : '',
      thumbnail: info.thumbnail || '',
      formats: (info.formats || []).map(f => ({
        quality: f.format_note || f.quality_label || f.resolution || f.acodec || f.vcodec || 'Audio',
        ext: f.ext,
        size: f.filesize ? (Math.round(f.filesize / 1024 / 1024) + 'MB') : '',
        format_id: f.format_id
      }))
    });
  } catch (err) {
    console.error('Info-Handler Exception:', err);
    res.status(500).json({ error: 'Failed to get media info.' });
  }
});

const sslOptions = {
  key: fs.readFileSync('/etc/letsencrypt/live/downloader.groupxyz.me/privkey.pem'),
  cert: fs.readFileSync('/etc/letsencrypt/live/downloader.groupxyz.me/fullchain.pem')
};

https.createServer(sslOptions, app).listen(PORT, '0.0.0.0', () => {
  console.log(`HTTPS Server läuft auf https://0.0.0.0:${PORT}`);
});
