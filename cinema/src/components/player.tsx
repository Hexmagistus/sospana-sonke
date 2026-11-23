"use client";

import { useEffect, useRef, useState } from "react";
import { playbackAllowed } from "@/lib/geo";
import { browserLibrary } from "@/lib/local-library";
import type { Movie, StreamSource } from "@/lib/types";
import { countryOptions } from "@/lib/countries";
import { formatRuntime } from "@/lib/utils";

function srtToVtt(srt: string): string {
  const body = srt.replace(/^\uFEFF/, "").replace(/\r+/g, "").trim();
  const cues = body
    .split(/\n{2,}/)
    .map((block) => {
      const lines = block.split("\n");
      const timeIndex = lines.findIndex((line) => line.includes("-->"));
      if (timeIndex < 0) return "";
      const timing = lines[timeIndex].replace(/,/g, ".");
      return `${timing}\n${lines.slice(timeIndex + 1).join("\n")}`;
    })
    .filter(Boolean);
  return `WEBVTT\n\n${cues.join("\n\n")}\n`;
}

export function Player({ movie, source, countries }: { movie: Movie; source: StreamSource; countries: string[] }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [country, setCountry] = useState("South Africa");
  const [message, setMessage] = useState<string | null>(null);
  const [captionMessage, setCaptionMessage] = useState<string | null>(null);
  const [speed, setSpeed] = useState(1);
  const gate = playbackAllowed(source, country);
  const options = countryOptions(countries);

  useEffect(() => {
    const saved = browserLibrary().read();
    setCountry(saved.country || "South Africa");
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || source.playbackType === "embed" || !gate.allowed) return;
    const saved = browserLibrary().read().progress.find((item) => item.slug === movie.slug);
    if (saved && saved.player !== "embed" && saved.position > 2) {
      const apply = () => {
        if (saved.position < (video.duration || saved.duration) - 2) video.currentTime = saved.position;
      };
      if (video.readyState >= 1) apply();
      else video.addEventListener("loadedmetadata", apply, { once: true });
    }
  }, [gate.allowed, movie.slug, source.playbackType]);

  useEffect(() => {
    if (source.playbackType !== "hls" || !gate.allowed) return;
    const video = videoRef.current;
    if (!video) return;
    let cancelled = false;
    let detach: () => void = () => undefined;
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = source.url;
      return;
    }
    import("hls.js")
      .then(({ default: Hls }) => {
        if (cancelled) return;
        if (!Hls.isSupported()) {
          setMessage("This browser cannot play the HLS stream.");
          return;
        }
        const hls = new Hls();
        hls.loadSource(source.url);
        hls.attachMedia(video);
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) setMessage(`The HLS stream failed: ${data.type} ${data.details}`);
        });
        detach = () => hls.destroy();
      })
      .catch((error: Error) => setMessage(`The HLS player could not load: ${error.message}`));
    return () => {
      cancelled = true;
      detach();
    };
  }, [gate.allowed, source.playbackType, source.url]);

  function remember(position: number, duration: number) {
    browserLibrary().saveProgress({
      slug: movie.slug,
      title: movie.title,
      position,
      duration: duration || movie.runtimeSeconds,
      updatedAt: new Date().toISOString(),
      player: source.playbackType,
    });
  }

  async function loadCaption(url: string) {
    setCaptionMessage(null);
    const video = videoRef.current;
    if (!video) return;
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const vtt = srtToVtt(await response.text());
      const track = video.addTextTrack("subtitles", "Captions", "en");
      const parser = vtt.split("\n\n").slice(1);
      for (const cueText of parser) {
        const [timing, ...lines] = cueText.split("\n");
        if (!timing?.includes("-->")) continue;
        const [start, end] = timing.split("-->").map((part) => toSeconds(part.trim()));
        if (Number.isFinite(start) && Number.isFinite(end)) track.addCue(new VTTCue(start, end, lines.join("\n")));
      }
      track.mode = "showing";
    } catch (error) {
      setCaptionMessage(
        `Captions could not be loaded from the archive (${error instanceof Error ? error.message : "unknown error"}). The caption file is still linked under the player.`,
      );
    }
  }

  if (!gate.allowed) {
    return (
      <div className="rounded-3xl border border-coral/40 bg-coral/10 p-6" data-testid="playback-blocked">
        <h2 className="font-display text-2xl">Playback is limited</h2>
        <p className="mt-2 text-sm">{gate.reason}</p>
        <CountrySelect country={country} options={options} onChange={setCountry} />
      </div>
    );
  }

  if (source.playbackType === "embed") {
    return (
      <div>
        <div className="aspect-video overflow-hidden rounded-3xl bg-black">
          <iframe
            data-testid="player-embed"
            src={source.url}
            title={`Official player for ${movie.title}`}
            className="h-full w-full"
            allow="fullscreen"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
          />
        </div>
        <p className="mt-3 text-sm text-ink/70">
          This is the provider&apos;s own player. It does not share a resume time with this site, so Continue watching opens it again from the start.
        </p>
        <button
          type="button"
          className="mt-3 text-sm text-amber"
          onClick={() => remember(0, movie.runtimeSeconds)}
        >
          Remember this title on this device
        </button>
        <p className="mt-3 text-xs text-ink/60">{gate.reason}</p>
        <CountrySelect country={country} options={options} onChange={setCountry} />
      </div>
    );
  }

  return (
    <div>
      <div className="overflow-hidden rounded-3xl bg-black">
        <video
          ref={videoRef}
          data-testid="player-video"
          className="aspect-video w-full"
          playsInline
          preload="metadata"
          src={source.playbackType === "mp4" ? source.url : undefined}
          onPlay={() => {
            const video = videoRef.current;
            if (video) remember(video.currentTime, video.duration);
          }}
          onPause={() => {
            const video = videoRef.current;
            if (video) remember(video.currentTime, video.duration);
          }}
          onTimeUpdate={() => {
            const video = videoRef.current;
            if (!video || Math.floor(video.currentTime) % 5 !== 0) return;
            remember(video.currentTime, video.duration);
          }}
        />
        <div className="flex flex-wrap items-center gap-3 bg-stone-950 px-3 py-3 text-sm">
          <button
            type="button"
            data-testid="player-play"
            className="rounded-full bg-amber px-3 py-1 font-semibold text-stone-950"
            onClick={() => {
              const video = videoRef.current;
              if (!video) return;
              if (video.paused) void video.play().catch((error: Error) => setMessage(error.message));
              else video.pause();
            }}
          >
            Play / pause
          </button>
          <label className="flex items-center gap-2">
            Volume
            <input
              aria-label="Volume"
              type="range"
              min={0}
              max={1}
              step={0.05}
              defaultValue={1}
              onChange={(event) => {
                if (videoRef.current) videoRef.current.volume = Number(event.target.value);
              }}
            />
          </label>
          <label className="flex items-center gap-2">
            Speed
            <select
              aria-label="Playback speed"
              value={speed}
              onChange={(event) => {
                const next = Number(event.target.value);
                setSpeed(next);
                if (videoRef.current) videoRef.current.playbackRate = next;
              }}
              className="rounded bg-stone-800 px-2 py-1"
            >
              {[0.75, 1, 1.25, 1.5].map((value) => (
                <option key={value} value={value}>
                  {value}×
                </option>
              ))}
            </select>
          </label>
          {source.subtitles.length > 0 ? (
            <label className="flex items-center gap-2">
              Captions
              <select
                aria-label="Captions"
                defaultValue=""
                onChange={(event) => {
                  if (event.target.value) void loadCaption(event.target.value);
                }}
                className="rounded bg-stone-800 px-2 py-1"
              >
                <option value="">Off</option>
                {source.subtitles.map((track) => (
                  <option key={track.url} value={track.url}>
                    {track.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button
            type="button"
            className="rounded-full border border-white/20 px-3 py-1"
            onClick={() => {
              const stage = videoRef.current?.parentElement;
              if (!stage) return;
              if (document.fullscreenElement) void document.exitFullscreen();
              else void stage.requestFullscreen();
            }}
          >
            Full screen
          </button>
          <span className="text-ink/60">{formatRuntime(movie.runtimeSeconds)}</span>
        </div>
      </div>
      {message ? <p className="mt-3 text-sm text-coral">{message}</p> : null}
      {captionMessage ? <p className="mt-3 text-sm text-amber">{captionMessage}</p> : null}
      <p className="mt-3 text-sm text-ink/70">{source.qualityNote}</p>
      <p className="mt-1 text-xs text-ink/60">{gate.reason}</p>
      <CountrySelect country={country} options={options} onChange={setCountry} />
    </div>
  );
}

function CountrySelect({
  country,
  options,
  onChange,
}: {
  country: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="mt-4 flex flex-wrap items-center gap-2 text-sm">
      Where you are watching
      <select
        aria-label="Where you are watching"
        value={country}
        onChange={(event) => {
          onChange(event.target.value);
          browserLibrary().setCountry(event.target.value);
        }}
        className="rounded-full border border-white/15 bg-black/40 px-3 py-1"
      >
        {options.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
    </label>
  );
}

function toSeconds(stamp: string): number {
  const [hours = "0", minutes = "0", seconds = "0"] = stamp.split(":");
  return Number(hours) * 3600 + Number(minutes) * 60 + Number(seconds);
}
