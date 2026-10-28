package com.quiz.rag.net;

import android.content.Context;
import android.content.SharedPreferences;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

import java.util.concurrent.TimeUnit;

public class ApiClient {

    // Works on a USB-connected phone via `adb reverse tcp:8000 tcp:8000`,
    // and on an emulator the same way. Override it on the login screen for
    // a LAN IP (http://192.168.x.x:8000/) or a deployed HTTPS URL.
    private static final String DEFAULT_BASE_URL = "http://127.0.0.1:8000/";
    private static ApiService service;
    private static String currentBaseUrl = DEFAULT_BASE_URL;

    public static synchronized ApiService get(Context context) {
        String savedUrl = getSavedBaseUrl(context);
        if (service == null || !savedUrl.equals(currentBaseUrl)) {
            currentBaseUrl = savedUrl;

            HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
            logging.setLevel(HttpLoggingInterceptor.Level.BODY);

            // Generous timeouts: PDF upload + AI question generation can take
            // well over a minute on the backend (it waits on the AI service).
            OkHttpClient client = new OkHttpClient.Builder()
                    .addInterceptor(logging)
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(90, TimeUnit.SECONDS)
                    .writeTimeout(60, TimeUnit.SECONDS)
                    .build();

            service = new Retrofit.Builder()
                    .baseUrl(currentBaseUrl)
                    .client(client)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
                    .create(ApiService.class);
        }
        return service;
    }

    public static String getSavedBaseUrl(Context context) {
        if (context == null) return DEFAULT_BASE_URL;
        SharedPreferences prefs = context.getSharedPreferences("rag_prefs", Context.MODE_PRIVATE);
        return prefs.getString("server_url", DEFAULT_BASE_URL);
    }

    public static void setSavedBaseUrl(Context context, String newUrl) {
        if (!newUrl.endsWith("/")) newUrl += "/";
        SharedPreferences prefs = context.getSharedPreferences("rag_prefs", Context.MODE_PRIVATE);
        prefs.edit().putString("server_url", newUrl).apply();
        service = null; // Forces rebuild on next get()
    }

    /** Derives the ws:// or wss:// URL for the game WebSocket from the REST base URL. */
    public static String getWsUrl(Context context) {
        String base = getSavedBaseUrl(context);
        if (base.startsWith("https://")) {
            base = "wss://" + base.substring("https://".length());
        } else if (base.startsWith("http://")) {
            base = "ws://" + base.substring("http://".length());
        }
        if (!base.endsWith("/")) base += "/";
        return base + "ws";
    }

    public static String bearer(Context context) {
        SharedPreferences prefs = context.getSharedPreferences("rag_prefs", Context.MODE_PRIVATE);
        return "Bearer " + prefs.getString("token", "");
    }
}