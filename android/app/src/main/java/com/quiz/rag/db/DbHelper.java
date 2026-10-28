package com.quiz.rag.db;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import com.quiz.rag.model.User;

/**
 * Lab Experiment 12: SQLite Database Helper
 * Provides offline local user registration, credential verification, and cached profiles.
 */
public class DbHelper extends SQLiteOpenHelper {

    private static final String DATABASE_NAME = "rag_quiz.db";
    private static final int DATABASE_VERSION = 1;

    // Users Table
    public static final String TABLE_USERS = "users";
    public static final String COL_ID = "id";
    public static final String COL_USERNAME = "username";
    public static final String COL_EMAIL = "email";
    public static final String COL_PASSWORD = "password";
    public static final String COL_ADDRESS = "address";
    public static final String COL_GENDER = "gender";
    public static final String COL_AGE = "age";
    public static final String COL_AVATAR = "avatar_id";

    // Match History Table
    public static final String TABLE_HISTORY = "history";
    public static final String COL_ROOM = "room_code";
    public static final String COL_OPPONENT = "opponent_name";
    public static final String COL_SCORE = "score";
    public static final String COL_RESULT = "result";

    public DbHelper(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        String createUsers = "CREATE TABLE " + TABLE_USERS + " ("
                + COL_ID + " INTEGER PRIMARY KEY AUTOINCREMENT,"
                + COL_USERNAME + " TEXT UNIQUE,"
                + COL_EMAIL + " TEXT,"
                + COL_PASSWORD + " TEXT,"
                + COL_ADDRESS + " TEXT,"
                + COL_GENDER + " TEXT,"
                + COL_AGE + " INTEGER,"
                + COL_AVATAR + " INTEGER)";

        String createHistory = "CREATE TABLE " + TABLE_HISTORY + " ("
                + COL_ID + " INTEGER PRIMARY KEY AUTOINCREMENT,"
                + COL_ROOM + " TEXT,"
                + COL_OPPONENT + " TEXT,"
                + COL_SCORE + " INTEGER,"
                + COL_RESULT + " TEXT)";

        db.execSQL(createUsers);
        db.execSQL(createHistory);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_USERS);
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_HISTORY);
        onCreate(db);
    }

    /**
     * Exp 7, 8, 12: Insert newly registered user into local SQLite database
     */
    public boolean registerUser(String username, String email, String password, String address, String gender, int age, int avatarId) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues cv = new ContentValues();
        cv.put(COL_USERNAME, username);
        cv.put(COL_EMAIL, email);
        cv.put(COL_PASSWORD, password);
        cv.put(COL_ADDRESS, address);
        cv.put(COL_GENDER, gender);
        cv.put(COL_AGE, age);
        cv.put(COL_AVATAR, avatarId);

        long result = db.insertWithOnConflict(TABLE_USERS, null, cv, SQLiteDatabase.CONFLICT_REPLACE);
        return result != -1;
    }

    /**
     * Exp 12: Authenticate user from SQLite offline cache
     */
    public boolean checkLogin(String usernameOrEmail, String password) {
        SQLiteDatabase db = this.getReadableDatabase();
        String query = "SELECT * FROM " + TABLE_USERS + " WHERE (" + COL_USERNAME + "=? OR " + COL_EMAIL + "=?) AND " + COL_PASSWORD + "=?";
        Cursor cursor = db.rawQuery(query, new String[]{usernameOrEmail, usernameOrEmail, password});
        boolean exists = cursor.getCount() > 0;
        cursor.close();
        return exists;
    }

    /**
     * Create or update the extended profile fields (address/gender/age) for a
     * username. The backend has no columns for these, so they only ever live
     * here. Works whether or not a local row already exists for this user
     * (e.g. someone who registered on the web and only guest-logged-in here).
     */
    public void upsertProfileDetails(String username, String address, String gender, int age) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues cv = new ContentValues();
        cv.put(COL_ADDRESS, address);
        cv.put(COL_GENDER, gender);
        cv.put(COL_AGE, age);

        int rows = db.update(TABLE_USERS, cv, COL_USERNAME + "=?", new String[]{username});
        if (rows == 0) {
            cv.put(COL_USERNAME, username);
            db.insertWithOnConflict(TABLE_USERS, null, cv, SQLiteDatabase.CONFLICT_IGNORE);
        }
    }

    /**
     * Retrieve local user profile
     */
    public User getUserProfile(String usernameOrEmail) {
        SQLiteDatabase db = this.getReadableDatabase();
        String query = "SELECT * FROM " + TABLE_USERS + " WHERE " + COL_USERNAME + "=? OR " + COL_EMAIL + "=?";
        Cursor c = db.rawQuery(query, new String[]{usernameOrEmail, usernameOrEmail});
        User user = null;
        if (c.moveToFirst()) {
            user = new User(
                    c.getString(c.getColumnIndexOrThrow(COL_USERNAME)),
                    c.getString(c.getColumnIndexOrThrow(COL_EMAIL)),
                    c.getString(c.getColumnIndexOrThrow(COL_ADDRESS)),
                    c.getString(c.getColumnIndexOrThrow(COL_GENDER)),
                    c.getInt(c.getColumnIndexOrThrow(COL_AGE)),
                    c.getInt(c.getColumnIndexOrThrow(COL_AVATAR))
            );
        }
        c.close();
        return user;
    }
}