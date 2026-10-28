package com.quiz.rag.net;

import java.util.Map;

import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.Header;
import retrofit2.http.Multipart;
import retrofit2.http.POST;
import retrofit2.http.PUT;
import retrofit2.http.Part;

/**
 * Mirrors the REAL backend routes in backend/main.py.
 * Real-time gameplay does NOT go through REST - it is all WebSocket
 * events on /ws, handled by {@link GameSocket}.
 */
public interface ApiService {

    @POST("api/auth/signup")
    Call<Map<String, Object>> signup(@Body Map<String, String> body);

    @POST("api/auth/login")
    Call<Map<String, Object>> login(@Body Map<String, String> body);

    @POST("api/auth/guest")
    Call<Map<String, Object>> guestLogin();

    @GET("api/auth/me")
    Call<Map<String, Object>> me(@Header("Authorization") String bearerToken);

    @GET("api/profile/history")
    Call<Map<String, Object>> history(@Header("Authorization") String bearerToken);

    @PUT("api/profile/update")
    Call<Map<String, Object>> updateProfile(@Header("Authorization") String bearerToken, @Body Map<String, String> body);

    @GET("api/health")
    Call<Map<String, Object>> health();

    /**
     * Matches POST /api/rooms/create-with-pdf: uploads a document and has the
     * AI service generate a quiz from it. Returns {room_code, questions_generated, ...}.
     * The host still has to join the room over the WebSocket afterward, same as
     * joining any other 1v1 room.
     */
    @Multipart
    @POST("api/rooms/create-with-pdf")
    Call<Map<String, Object>> createRoomWithPdf(
            @Header("Authorization") String bearerToken,
            @Part MultipartBody.Part file,
            @Part("questions_count") RequestBody questionsCount,
            @Part("time_per_question") RequestBody timePerQuestion,
            @Part("difficulty") RequestBody difficulty,
            @Part("mode") RequestBody mode
    );
}
