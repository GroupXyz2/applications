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
    console.log('Download request:', url, 'Quality:', quality);
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
      const path = require('path');
      const fs = require('fs');
      const { spawn } = require('child_process');
      let responded = false;
      let errorOutput = '';
      const scriptDir = process.cwd();
      const spotdl = spawn('spotdl', [spotUrl, '--format', 'mp3', '--bitrate', '192k'], { stdio: ['ignore', 'pipe', 'pipe'] });
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
        fs.readdir(scriptDir, (dirErr, files) => {
          if (dirErr) {
            res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
            res.setHeader('Content-Type', 'text/plain');
            res.end('Spotify download failed!\n' + errorOutput + '\n' + dirErr.toString());
            return;
          }
          const mp3Files = files.filter(f => f.endsWith('.mp3')).map(f => {
            const fullPath = path.join(scriptDir, f);
            let mtime = 0;
            try { mtime = fs.statSync(fullPath).mtimeMs; } catch { mtime = 0; }
            return { file: f, mtime };
          }).sort((a, b) => b.mtime - a.mtime);
          if (!mp3Files.length) {
            const log = errorOutput + '\nNo MP3 file found.';
            res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
            res.setHeader('Content-Type', 'text/plain');
            res.end('Spotify download failed!\n' + log);
            return;
          }
          const mp3File = mp3Files[0].file;
          const mp3Path = path.join(scriptDir, mp3File);
          fs.readFile(mp3Path, (err, buffer) => {
            fs.unlink(mp3Path, () => {});
            if (code !== 0 || err || !buffer || buffer.length < 1000) {
              const log = errorOutput + '\n' + (buffer ? buffer.toString() : '');
              res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
              res.setHeader('Content-Type', 'text/plain');
              res.end('Spotify download failed!\n' + log);
              return;
            }
            const filename = mp3File;
            res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
            res.setHeader('Content-Type', 'audio/mpeg');
            res.end(buffer);
          });
        });
      });
      return;
    }

    if (!quality || typeof quality !== 'string' || !quality.trim()) {
      return res.status(400).json({ error: 'No format specified.' });
    }

    const info = await exec(url, {
      dumpSingleJson: true,
      noWarnings: true,
      noCheckCertificate: true,
      preferFreeFormats: true,
      youtubeSkipDashManifest: true
    });

    const title = sanitizeFilename(info.title || 'download_groupxyz.me');
    let ext = 'mp4';
    if (quality.includes('mp3')) ext = 'mp3';
    else if (quality.includes('m4a')) ext = 'm4a';
    else if (quality.includes('webm')) ext = 'webm';
    const filename = `${title}.${ext}`;

    const tempFiles = [];
    const tmp = require('os').tmpdir();
    const path = require('path');
    const { v4: uuidv4 } = require('uuid');
    const tempBase = path.join(tmp, 'ytdl_' + uuidv4());
    const tempInput = tempBase + '_input';
    const tempOutput = tempBase + '_output';
    let mp4Output = tempBase + '.mp4';

    let ytdlpFormat = 'bestaudio/best';
    let ytdlpArgs = [];
    if (ext === 'mp4') {
      ytdlpFormat = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best';
      ytdlpArgs = [
        '-f', ytdlpFormat,
        '--merge-output-format', 'mp4',
        '-o', mp4Output,
        url
      ];
    } else {
      ytdlpArgs = [
        '-f', ytdlpFormat,
        '-o', tempInput,
        url
      ];
    }
    const ytdlp = spawn('yt-dlp', ytdlpArgs, { stdio: ['ignore', 'pipe', 'pipe'] });

    let errorOutput = '';
    let responded = false;
    ytdlp.stderr.on('data', (data) => {
      errorOutput += data.toString();
      console.error(`[yt-dlp] ${data}`);
    });
    ytdlp.on('error', (err) => {
      console.error('yt-dlp error:', err);
      if (!responded) {
        responded = true;
        res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
        res.setHeader('Content-Type', 'text/plain');
        res.end('Error during download.\n' + (err.message || ''));
        cleanupTempFiles();
      }
    });
    ytdlp.on('close', (code) => {
      if (responded) return;
      if (ext === 'mp4') {
        fs.readFile(mp4Output, (err, buffer) => {
          responded = true;
          if (code !== 0 || err || !buffer || buffer.length < 1000) {
            const log = errorOutput + '\n' + (buffer ? buffer.toString() : '');
            res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
            res.setHeader('Content-Type', 'text/plain');
            res.end('yt-dlp failed or did not return a valid mp4 file!\n' + log);
            cleanupTempFiles();
            return;
          }
          res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
          res.setHeader('Content-Type', 'video/mp4');
          res.end(buffer);
          cleanupTempFiles();
        });
        tempFiles.push(mp4Output);
        return;
      }
      fs.readFile(tempInput, (err, buffer) => {
        if (code !== 0 || err || !buffer || buffer.length < 1000) {
          responded = true;
          const log = errorOutput + '\n' + (buffer ? buffer.toString() : '');
          res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
          res.setHeader('Content-Type', 'text/plain');
          res.end('yt-dlp failed or did not return a valid file!\n' + log);
          cleanupTempFiles();
          return;
        }
        if (ext === 'mp3' || ext === 'm4a' || ext === 'webm') {
          const ffmpeg = spawn('ffmpeg', [
            '-i', tempInput,
            '-vn',
            '-acodec', ext === 'mp3' ? 'libmp3lame' : (ext === 'm4a' ? 'aac' : 'libvorbis'),
            '-f', ext,
            tempOutput
          ], { stdio: ['ignore', 'pipe', 'pipe'] });
          tempFiles.push(tempOutput);
          let ffmpegErr = '';
          ffmpeg.stderr.on('data', (d) => ffmpegErr += d.toString());
          ffmpeg.on('error', (err) => {
            if (!responded) {
              responded = true;
              res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
              res.setHeader('Content-Type', 'text/plain');
              res.end('ffmpeg error converting file.\n' + (err.message || ''));
              cleanupTempFiles();
            }
          });
          ffmpeg.on('close', (ffcode) => {
            if (responded) return;
            fs.readFile(tempOutput, (err2, outBuffer) => {
              responded = true;
              if (ffcode !== 0 || err2 || !outBuffer || outBuffer.length < 1000) {
                res.setHeader('Content-Disposition', 'attachment; filename="error.log"');
                res.setHeader('Content-Type', 'text/plain');
                res.end('ffmpeg failed to convert file!\n' + ffmpegErr);
                cleanupTempFiles();
                return;
              }
              res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
              res.setHeader('Content-Type', ext === 'mp3' ? 'audio/mpeg' : (ext === 'm4a' ? 'audio/mp4' : 'audio/webm'));
              res.end(outBuffer);
              cleanupTempFiles();
            });
          });
        } else {
          responded = true;
          res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
          res.setHeader('Content-Type', 'application/octet-stream');
          res.end(buffer);
          cleanupTempFiles();
        }
      });
    });

    function cleanupTempFiles() {
      for (const f of tempFiles) {
        fs.unlink(f, () => {});
      }
    }
    return;
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
      const spotdl = spawn('spotdl', ['meta', spotUrl, 'json']);
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
