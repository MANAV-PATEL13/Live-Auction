# Bhaktipurv API Documentation

Welcome to the **Bhaktipurv API** reference documentation. All APIs are built using FastAPI and MongoDB (Beanie ODM).

> **Frontend Stack:** Flutter (supports both **Android** and **Web** via `http` package)
> **Base URL:** `http://127.0.0.1:3000` (replace with your actual deployment URL)

---

## Standard Response Structure

All API responses follow a standardized JSON wrapper:

```json
{
  "success": true,
  "code": 200,
  "message": "Operation response message",
  "data": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | `true` if operation succeeded, `false` on error |
| `code` | `int` | HTTP status code |
| `message` | `string` | Human-readable result description |
| `data` | `object \| array \| null` | Payload |

---

## Flutter Setup

### Dependencies (`pubspec.yaml`)
```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
  shared_preferences: ^2.2.2
```

### API Client Base (`lib/core/api_client.dart`)
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String baseUrl = 'https://api.bhaktipurv.com';

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  static Future<Map<String, String>> headers({bool auth = false}) async {
    final map = {'Content-Type': 'application/json'};
    if (auth) {
      final token = await getToken();
      if (token != null) map['Authorization'] = 'Bearer $token';
    }
    return map;
  }
}
```

---

## Access Levels

| Role | Description |
|------|-------------|
| **Normal User** | Authenticated user with basic permissions |
| **Admin / Privileged User** | User with elevated permission groups |
| **Superuser** | Full system access (`is_superuser: true`) |

---

## Table of Contents

1. [System / Root](#1-system--root)
2. [Authentication](#2-authentication)
3. [Users Management](#3-users-management)
4. [Permissions Management](#4-permissions-management)
5. [Permission Groups Management](#5-permission-groups-management)
6. [Canteen Management](#6-canteen-management)
7. [Teams Management](#7-teams-management)
8. [Team Assignments](#8-team-assignments)
9. [App Configuration](#9-app-configuration)
10. [Session Management](#10-session-management)
11. [Registration Management](#11-registration-management)
12. [Auction Management](#12-auction-management)
13. [Error Handling](#13-error-handling)
14. [Platform Notes](#14-platform-notes)

---

## 1. System / Root

### `GET /app`
Get system welcome message and version metadata.

- **Authorization:** None Required
- **Access:** Public

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Welcome to Bhaktipurv",
  "data": {
    "name": "Bhaktipurv API",
    "version": "1.0.0"
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> getAppInfo() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/app'),
    headers: await ApiClient.headers(),
  );
  return jsonDecode(response.body);
}
```

---

## 2. Authentication

Base Route: `/auth`

---

### `POST /auth/register`
Register a new user account.

- **Authorization:** None Required
- **Access:** Public

#### Request Body
```json
{
  "first_name": "Rahul",
  "middle_name": "Kumar",
  "last_name": "Sharma",
  "roll_no": "CS202601",
  "email": "rahul.sharma@bhaktipurv.com",
  "mobile": "+919876543210",
  "password": "SecurePassword@123"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User registered successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "email": "rahul.sharma@bhaktipurv.com"
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> register({
  required String firstName,
  String? middleName,
  required String lastName,
  required String rollNo,
  required String email,
  required String mobile,
  required String password,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auth/register'),
    headers: await ApiClient.headers(),
    body: jsonEncode({
      'first_name': firstName,
      'middle_name': middleName,
      'last_name': lastName,
      'roll_no': rollNo,
      'email': email,
      'mobile': mobile,
      'password': password,
    }),
  );
  return jsonDecode(response.body);
}
```

---

### `POST /auth/login`
Authenticate user credentials and issue access + refresh tokens.

- **Authorization:** None Required
- **Access:** Public

#### Request Body — Android
```json
{
  "email": "rahul.sharma@bhaktipurv.com",
  "password": "SecurePassword@123",
  "device_id": "android-uuid-abc123",
  "device_name": "Samsung Galaxy S24",
  "platform": "android"
}
```

#### Request Body — Web
```json
{
  "email": "rahul.sharma@bhaktipurv.com",
  "password": "SecurePassword@123",
  "device_id": "web-session-1725357000000",
  "device_name": "Flutter Web Browser",
  "platform": "web"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### Flutter Example — Android
```dart
Future<Map<String, dynamic>> loginAndroid({
  required String email,
  required String password,
  required String deviceId,
  required String deviceName,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auth/login'),
    headers: await ApiClient.headers(),
    body: jsonEncode({
      'email': email,
      'password': password,
      'device_id': deviceId,
      'device_name': deviceName,
      'platform': 'android',
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', data['data']['access_token']);
    await prefs.setString('refresh_token', data['data']['refresh_token']);
  }
  return data;
}
```

#### Flutter Example — Web
```dart
Future<Map<String, dynamic>> loginWeb({
  required String email,
  required String password,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auth/login'),
    headers: await ApiClient.headers(),
    body: jsonEncode({
      'email': email,
      'password': password,
      'device_id': 'web-session-${DateTime.now().millisecondsSinceEpoch}',
      'device_name': 'Flutter Web Browser',
      'platform': 'web',
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', data['data']['access_token']);
    await prefs.setString('refresh_token', data['data']['refresh_token']);
  }
  return data;
}
```

---

### `POST /auth/logout`
Logout user and deactivate the current device session.

- **Authorization:** `Bearer <access_token>`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Logout successful",
  "data": null
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> logout() async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auth/logout'),
    headers: await ApiClient.headers(auth: true),
  );
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove('access_token');
  await prefs.remove('refresh_token');
  return jsonDecode(response.body);
}
```

---

### `POST /auth/refresh`
Generate a new JWT access token using a valid refresh token.

- **Authorization:** None Required
- **Access:** Public (uses refresh token)

#### Request Body
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Access token refreshed successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> refreshToken() async {
  final prefs = await SharedPreferences.getInstance();
  final refreshTkn = prefs.getString('refresh_token');
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auth/refresh'),
    headers: await ApiClient.headers(),
    body: jsonEncode({'refresh_token': refreshTkn}),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) {
    await prefs.setString('access_token', data['data']['access_token']);
  }
  return data;
}
```

---

## 3. Users Management

Base Route: `/users`

---

### `GET /users`
Fetch all registered users.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:view`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Users fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "name": "Rahul Kumar Sharma",
      "first_name": "Rahul",
      "middle_name": "Kumar",
      "last_name": "Sharma",
      "roll_no": "CS202601",
      "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
      "email": "rahul.sharma@bhaktipurv.com",
      "mobile": "+919876543210",
      "image_url": "https://example.com/avatar.jpg",
      "is_active": true,
      "is_allowed": true,
      "is_superuser": false
    }
  ]
}
```

#### Flutter Example — Admin View
```dart
// Admin only: fetch full user listing
Future<List<dynamic>> getAllUsers() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/users'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

> **Normal User:** This endpoint returns 403 Forbidden. Hide admin-only navigation from normal users in the UI.

---

### `GET /users/me`
Fetch current logged-in user profile.

- **Authorization:** `Bearer <access_token>`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Current user fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "email": "rahul.sharma@bhaktipurv.com",
    "image_url": "https://example.com/avatar.jpg",
    "is_active": true,
    "is_allowed": true,
    "is_superuser": false
  }
}
```

#### Flutter Example — Normal User & Admin
```dart
Future<Map<String, dynamic>> getMyProfile() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/users/me'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /users/{user_id}`
Fetch single user details by user ID.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:view`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "first_name": "Rahul",
    "middle_name": "Kumar",
    "last_name": "Sharma",
    "roll_no": "CS202601",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "email": "rahul.sharma@bhaktipurv.com",
    "mobile": "+919876543210",
    "image_url": "https://example.com/avatar.jpg",
    "is_active": true,
    "is_allowed": true,
    "is_superuser": false
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> getUserById(String userId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/users/$userId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /users/{user_id}`
Update user details and profile information.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:update`
- **Access:** Admin / Privileged User only

#### Request Body
All fields are optional; supply only the fields to update:
```json
{
  "first_name": "Rahul",
  "middle_name": "Kumar",
  "last_name": "Sharma",
  "base_price": 500,
  "group_ids": [
    "64f1a2b3c4d5e6f7a8b9c0f1"
  ],
  "roll_no": "CS202601",
  "email": "rahul.sharma@bhaktipurv.com",
  "mobile": "+919876543210",
  "image_url": "https://example.com/avatar_updated.jpg",
  "is_active": true,
  "is_allowed": true
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "first_name": "Rahul",
    "middle_name": "Kumar",
    "last_name": "Sharma",
    "roll_no": "CS202601",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "email": "rahul.sharma@bhaktipurv.com",
    "mobile": "+919876543210",
    "image_url": "https://example.com/avatar_updated.jpg",
    "is_active": true,
    "is_allowed": true,
    "is_superuser": false
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updateUser({
  required String userId,
  String? firstName,
  String? middleName,
  String? lastName,
  int? basePrice,
  List<String>? groupIds,
  String? rollNo,
  String? email,
  String? mobile,
  String? imageUrl,
  bool? isActive,
  bool? isAllowed,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/users/$userId'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (firstName != null) 'first_name': firstName,
      if (middleName != null) 'middle_name': middleName,
      if (lastName != null) 'last_name': lastName,
      if (basePrice != null) 'base_price': basePrice,
      if (groupIds != null) 'group_ids': groupIds,
      if (rollNo != null) 'roll_no': rollNo,
      if (email != null) 'email': email,
      if (mobile != null) 'mobile': mobile,
      if (imageUrl != null) 'image_url': imageUrl,
      if (isActive != null) 'is_active': isActive,
      if (isAllowed != null) 'is_allowed': isAllowed,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /users/{user_id}/groups`
Assign permission groups to a user.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:update`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "group_ids": [
    "64f1a2b3c4d5e6f7a8b9c0f1",
    "64f1a2b3c4d5e6f7a8b9c0f2"
  ]
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User groups updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "email": "rahul.sharma@bhaktipurv.com",
    "groups": [
      "64f1a2b3c4d5e6f7a8b9c0f1",
      "64f1a2b3c4d5e6f7a8b9c0f2"
    ]
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> assignUserGroups({
  required String userId,
  required List<String> groupIds,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/users/$userId/groups'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({'group_ids': groupIds}),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /users/{user_id}/activate`
Activate / permit a deactivated user account to access the app (`is_allowed = true`).

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:access`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User activated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "is_allowed": true
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> activateUser(String userId) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/users/$userId/activate'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /users/me/password`
Authenticated user changes their own password after verifying their current password.

- **Authorization:** `Bearer <access_token>`
- **Access:** All authenticated users

#### Request Body
```json
{
  "current_password": "SecurePassword@123",
  "new_password": "NewSecurePassword@456"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Password changed successfully",
  "data": null
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> changeMyPassword({
  required String currentPassword,
  required String newPassword,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/users/me/password'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'current_password': currentPassword,
      'new_password': newPassword,
    }),
  );
  return jsonDecode(response.body);
}
```

---

### `PUT /users/{user_id}/password`
Admin resets a user's password to the default pattern configured in environment settings (`.env` -> `RESET_PASSWORD_PATTERN`).

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:update`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Password reset to default successfully",
  "data": null
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> resetUserPassword(String userId) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/users/$userId/password'),
    headers: await ApiClient.headers(auth: true),
  );
  return jsonDecode(response.body);
}
```

---

### `PUT /users/{user_id}/deactivate`
Deactivate / restrict an active user account from accessing the app (`is_allowed = false`).

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:access`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User deactivated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "is_allowed": false
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> deactivateUser(String userId) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/users/$userId/deactivate'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `DELETE /users/{user_id}`
Delete a user account permanently.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:delete`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User deleted successfully",
  "data": null
}
```

#### Flutter Example — Admin View
```dart
Future<bool> deleteUser(String userId) async {
  final response = await http.delete(
    Uri.parse('${ApiClient.baseUrl}/users/$userId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  return data['success'] == true;
}
```

---

### `POST /users/import`
Import users in bulk from a CSV file.

> **Password Note:** The CSV does **not** include a password column. Passwords are automatically generated using the user's `roll_no` in the format: `{roll_no}@321` (e.g., if `roll_no` is `452`, the generated password will be `452@321`).

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:create`
- **Access:** Admin / Privileged User only
- **Content-Type:** `multipart/form-data`

#### CSV Columns:
- `first_name` (required)
- `middle_name` (optional)
- `last_name` (required)
- `roll_no` (required - used for automatic password generation: `<roll_no>@321`)
- `email` (required)
- `mobile` (optional)
- `image_url` (optional)

#### Request (Multipart Form Data)
| Key | Type | Description |
|---|---|---|
| `file` | File (`.csv`) | The CSV file to upload |

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User CSV import completed",
  "data": {
    "total_rows": 2,
    "created": 2,
    "failed": 0,
    "report": [
      {
        "row": 2,
        "status": "created",
        "reason": null
      },
      {
        "row": 3,
        "status": "created",
        "reason": null
      }
    ]
  }
}
```

---

### `GET /users/import/template`
Download the standard CSV template for bulk user import.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:create`
- **Access:** Admin / Privileged User only

#### Response
- **Content-Type:** `text/csv`
- **File:** `users_import_template.csv`

---

### `GET /users/export`
Export all users as a CSV file.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:view`
- **Access:** Admin / Privileged User only

#### Response
- **Content-Type:** `text/csv`
- **File:** `users_export.csv`

#### Flutter Example — Admin View
```dart
Future<String> exportUsersCsv() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/users/export'),
    headers: await ApiClient.headers(auth: true),
  );
  return response.body;
}
```

---

### `POST /users/base-price/import`
Import player auction base prices in bulk from a CSV file. The user must be registered for event participation (`is_registered = true`).

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:update`
- **Access:** Admin / Privileged User only
- **Content-Type:** `multipart/form-data`

#### CSV Columns:
- `roll_no` (required - unique student roll number)
- `base_price` (required - non-negative integer, base bid price in Pushp)

#### Request (Multipart Form Data)
| Key | Type | Description |
|---|---|---|
| `file` | File (`.csv`) | The CSV file containing base price data |

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Base price CSV import completed",
  "data": {
    "total_rows": 2,
    "updated": 2,
    "failed": 0,
    "report": [
      {
        "row": 2,
        "status": "updated",
        "reason": "Base price updated to 500"
      },
      {
        "row": 3,
        "status": "updated",
        "reason": "Base price updated to 800"
      }
    ]
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> importBasePrices({
  required List<int> fileBytes,
  required String filename,
}) async {
  final request = http.MultipartRequest(
    'POST',
    Uri.parse('${ApiClient.baseUrl}/users/base-price/import'),
  );
  request.headers.addAll(await ApiClient.headers(auth: true));
  request.files.add(
    http.MultipartFile.fromBytes('file', fileBytes, filename: filename),
  );
  final streamedResponse = await request.send();
  final response = await http.Response.fromStream(streamedResponse);
  return jsonDecode(response.body);
}
```

---

### `GET /users/base-price/import/template`
Download standard CSV template for importing user base prices.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `user:update`
- **Access:** Admin / Privileged User only

#### Response
- **Content-Type:** `text/csv`
- **File:** `base_price_import_template.csv`

#### Flutter Example — Admin View
```dart
Future<String> downloadBasePriceTemplate() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/users/base-price/import/template'),
    headers: await ApiClient.headers(auth: true),
  );
  return response.body; // CSV text: "roll_no,base_price\n101,500\n"
}
```

---

## 4. Permissions Management

Base Route: `/permissions`

> All endpoints in this section require Admin / Privileged User access.

---

### `POST /permissions`
Create a new permission entry.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission:create`

#### Request Body
```json
{
  "name": "View Canteen Items",
  "code": "canteen:item:view",
  "description": "Allows viewing menu items in the canteen"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 201,
  "message": "Permission created successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0e1",
    "name": "View Canteen Items",
    "code": "canteen:item:view",
    "description": "Allows viewing menu items in the canteen"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> createPermission({
  required String name,
  required String code,
  String? description,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/permissions'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'name': name,
      'code': code,
      'description': description,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /permissions`
Get all defined permissions.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission:view`

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permissions fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c0e1",
      "name": "View Canteen Items",
      "code": "canteen:item:view",
      "description": "Allows viewing menu items in the canteen"
    },
    {
      "id": "64f1a2b3c4d5e6f7a8b9c0e2",
      "name": "Create Canteen Items",
      "code": "canteen:item:create",
      "description": "Allows creating new menu items"
    }
  ]
}
```

#### Flutter Example — Admin View
```dart
Future<List<dynamic>> getAllPermissions() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/permissions'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `GET /permissions/{permission_id}`
Fetch permission details by ID.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission:view`

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permission fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0e1",
    "name": "View Canteen Items",
    "code": "canteen:item:view",
    "description": "Allows viewing menu items in the canteen"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> getPermissionById(String permissionId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/permissions/$permissionId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /permissions/{permission_id}`
Update an existing permission.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission:update`

#### Request Body
```json
{
  "name": "View Canteen Items (Updated)",
  "code": "canteen:item:view",
  "description": "Updated description for viewing canteen menu items",
  "is_active": true
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permission updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0e1",
    "name": "View Canteen Items (Updated)",
    "code": "canteen:item:view",
    "description": "Updated description for viewing canteen menu items",
    "is_active": true
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updatePermission({
  required String permissionId,
  String? name,
  String? code,
  String? description,
  bool? isActive,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/permissions/$permissionId'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (name != null) 'name': name,
      if (code != null) 'code': code,
      if (description != null) 'description': description,
      if (isActive != null) 'is_active': isActive,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `DELETE /permissions/{permission_id}`
Delete a permission permanently.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission:delete`

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permission deleted successfully",
  "data": null
}
```

#### Flutter Example — Admin View
```dart
Future<bool> deletePermission(String permissionId) async {
  final response = await http.delete(
    Uri.parse('${ApiClient.baseUrl}/permissions/$permissionId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  return data['success'] == true;
}
```

---

## 5. Permission Groups Management

Base Route: `/permission-groups`

> All endpoints require Admin / Privileged User access.

---

### `POST /permission-groups`
Create a new permission group.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission_group:create`

#### Request Body
```json
{
  "name": "Canteen Managers",
  "description": "Group for staff managing canteen menu and orders",
  "permission_ids": [
    "64f1a2b3c4d5e6f7a8b9c0e1",
    "64f1a2b3c4d5e6f7a8b9c0e2"
  ]
}
```

#### Response Example
```json
{
  "success": true,
  "code": 201,
  "message": "Permission group created successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0f1",
    "name": "Canteen Managers",
    "description": "Group for staff managing canteen menu and orders",
    "permission_ids": [
      "64f1a2b3c4d5e6f7a8b9c0e1",
      "64f1a2b3c4d5e6f7a8b9c0e2"
    ]
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> createPermissionGroup({
  required String name,
  String? description,
  required List<String> permissionIds,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/permission-groups'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'name': name,
      'description': description,
      'permission_ids': permissionIds,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /permission-groups`
Fetch all permission groups.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission_group:view`

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permission groups fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c0f1",
      "name": "Canteen Managers",
      "description": "Group for staff managing canteen menu and orders",
      "permission_ids": [
        "64f1a2b3c4d5e6f7a8b9c0e1",
        "64f1a2b3c4d5e6f7a8b9c0e2"
      ]
    }
  ]
}
```

#### Flutter Example — Admin View
```dart
Future<List<dynamic>> getAllPermissionGroups() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/permission-groups'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `GET /permission-groups/{group_id}`
Fetch single permission group by ID.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission_group:view`

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permission group fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0f1",
    "name": "Canteen Managers",
    "description": "Group for staff managing canteen menu and orders",
    "permission_ids": [
      "64f1a2b3c4d5e6f7a8b9c0e1",
      "64f1a2b3c4d5e6f7a8b9c0e2"
    ]
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> getPermissionGroupById(String groupId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/permission-groups/$groupId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /permission-groups/{group_id}`
Update an existing permission group.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission_group:update`

#### Request Body
```json
{
  "name": "Senior Canteen Managers",
  "description": "Senior staff managing canteen with extended access",
  "permission_ids": [
    "64f1a2b3c4d5e6f7a8b9c0e1",
    "64f1a2b3c4d5e6f7a8b9c0e2",
    "64f1a2b3c4d5e6f7a8b9c0e3"
  ],
  "is_active": true
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permission group updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0f1",
    "name": "Senior Canteen Managers",
    "description": "Senior staff managing canteen with extended access",
    "permission_ids": [
      "64f1a2b3c4d5e6f7a8b9c0e1",
      "64f1a2b3c4d5e6f7a8b9c0e2",
      "64f1a2b3c4d5e6f7a8b9c0e3"
    ],
    "is_active": true
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updatePermissionGroup({
  required String groupId,
  String? name,
  String? description,
  List<String>? permissionIds,
  bool? isActive,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/permission-groups/$groupId'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (name != null) 'name': name,
      if (description != null) 'description': description,
      if (permissionIds != null) 'permission_ids': permissionIds,
      if (isActive != null) 'is_active': isActive,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `DELETE /permission-groups/{group_id}`
Delete a permission group.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `permission_group:delete`

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Permission group deleted successfully",
  "data": null
}
```

#### Flutter Example — Admin View
```dart
Future<bool> deletePermissionGroup(String groupId) async {
  final response = await http.delete(
    Uri.parse('${ApiClient.baseUrl}/permission-groups/$groupId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  return data['success'] == true;
}
```

---

## 6. Canteen Management

Base Route: `/canteen`

---

### `POST /canteen`
Create a new menu item in the canteen.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `canteen:item:create`
- **Access:** Admin / Canteen Manager only

#### Request Body
```json
{
  "name": "Paneer Butter Masala",
  "description": "Rich creamy paneer dish served with Indian spices",
  "price": 180.0,
  "image_url": "https://example.com/images/paneer.jpg",
  "is_show": true
}
```

#### Response Example
```json
{
  "success": true,
  "code": 201,
  "message": "Menu item created successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c1a1",
    "name": "Paneer Butter Masala",
    "description": "Rich creamy paneer dish served with Indian spices",
    "price": 180.0,
    "image_url": "https://example.com/images/paneer.jpg",
    "is_show": true,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> createCanteenItem({
  required String name,
  required String description,
  required double price,
  String? imageUrl,
  bool isShow = true,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/canteen'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'name': name,
      'description': description,
      'price': price,
      'image_url': imageUrl,
      'is_show': isShow,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /canteen`
Fetch all canteen menu items.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `canteen:item:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Menu items fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c1a1",
      "name": "Paneer Butter Masala",
      "description": "Rich creamy paneer dish served with Indian spices",
      "price": 180.0,
      "image_url": "https://example.com/images/paneer.jpg",
      "is_show": true
    },
    {
      "id": "64f1a2b3c4d5e6f7a8b9c1a2",
      "name": "Dal Fry",
      "description": "Classic yellow dal with tempered spices",
      "price": 80.0,
      "image_url": "https://example.com/images/dal_fry.jpg",
      "is_show": true
    }
  ]
}
```

#### Flutter Example — Normal User View
```dart
// Normal user: read-only canteen menu
Future<List<dynamic>> getCanteenMenu() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/canteen'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

#### Flutter Example — Admin View
```dart
// Admin: same call, UI renders edit and delete buttons per item
Future<List<dynamic>> getCanteenMenuAdmin() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/canteen'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `GET /canteen/{item_id}`
Fetch single menu item by ID.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `canteen:item:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Menu item fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c1a1",
    "name": "Paneer Butter Masala",
    "description": "Rich creamy paneer dish served with Indian spices",
    "price": 180.0,
    "image_url": "https://example.com/images/paneer.jpg",
    "is_show": true
  }
}
```

#### Flutter Example — Normal User & Admin
```dart
Future<Map<String, dynamic>> getCanteenItemById(String itemId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/canteen/$itemId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /canteen/{item_id}`
Update a canteen menu item.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `canteen:item:update`
- **Access:** Admin / Canteen Manager only

#### Request Body
```json
{
  "name": "Special Paneer Butter Masala",
  "price": 195.0,
  "image_url": "https://example.com/images/paneer_special.jpg",
  "description": "Special recipe paneer butter masala with extra cream",
  "is_show": true
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Menu item updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c1a1",
    "name": "Special Paneer Butter Masala",
    "description": "Special recipe paneer butter masala with extra cream",
    "price": 195.0,
    "image_url": "https://example.com/images/paneer_special.jpg",
    "is_show": true
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updateCanteenItem({
  required String itemId,
  String? name,
  String? description,
  double? price,
  String? imageUrl,
  bool? isShow,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/canteen/$itemId'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (name != null) 'name': name,
      if (description != null) 'description': description,
      if (price != null) 'price': price,
      if (imageUrl != null) 'image_url': imageUrl,
      if (isShow != null) 'is_show': isShow,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `DELETE /canteen/{item_id}`
Delete a canteen menu item.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `canteen:item:delete`
- **Access:** Admin only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Menu item deleted successfully",
  "data": null
}
```

#### Flutter Example — Admin View
```dart
Future<bool> deleteCanteenItem(String itemId) async {
  final response = await http.delete(
    Uri.parse('${ApiClient.baseUrl}/canteen/$itemId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  return data['success'] == true;
}
```

---

## 7. Teams Management

Base Route: `/teams`

---

### `POST /teams`
Create a new team.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:create`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "name": "Strikers XI",
  "code": "STK",
  "image_url": "https://example.com/logos/strikers.png",
  "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d2",
  "is_active": true
}
```

#### Response Example
```json
{
  "success": true,
  "code": 201,
  "message": "Team created successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "name": "Strikers XI",
    "code": "STK",
    "image_url": "https://example.com/logos/strikers.png",
    "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d2",
    "is_active": true,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> createTeam({
  required String name,
  required String code,
  String? imageUrl,
  required String captainId,
  String? viceCaptainId,
  bool isActive = true,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/teams'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'name': name,
      'code': code,
      'image_url': imageUrl,
      'captain_id': captainId,
      'vice_captain_id': viceCaptainId,
      'is_active': isActive,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /teams`
Fetch all teams.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Teams fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c2b1",
      "name": "Strikers XI",
      "code": "STK",
      "image_url": "https://example.com/logos/strikers.png",
      "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d2",
      "is_active": true
    },
    {
      "id": "64f1a2b3c4d5e6f7a8b9c2b2",
      "name": "Warriors FC",
      "code": "WFC",
      "image_url": "https://example.com/logos/warriors.png",
      "captain_id": "64f1a2b3c4d5e6f7a8b9c0d3",
      "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d4",
      "is_active": true
    }
  ]
}
```

#### Flutter Example — Normal User View
```dart
Future<List<dynamic>> getAllTeams() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/teams'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

#### Flutter Example — Admin View
```dart
// Admin: same call, UI renders edit and delete buttons
Future<List<dynamic>> getAllTeamsAdmin() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/teams'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `GET /teams/users/{user_id}/team`
Fetch the team that a specific user currently belongs to.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "user team fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "name": "Strikers XI",
    "code": "STK",
    "image_url": "https://example.com/logos/strikers.png",
    "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d2",
    "initial_balance": 6250,
    "balance": 5250,
    "is_active": true,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>?> getUserTeam(String userId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/teams/users/$userId/team'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /teams/{team_id}`
Fetch team details by ID.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Team fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "name": "Strikers XI",
    "code": "STK",
    "image_url": "https://example.com/logos/strikers.png",
    "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d2",
    "is_active": true
  }
}
```

#### Flutter Example — Normal User & Admin
```dart
Future<Map<String, dynamic>> getTeamById(String teamId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /teams/{team_id}`
Update team information.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:update`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "name": "Strikers United",
  "code": "STU",
  "image_url": "https://example.com/logos/strikers_united.png",
  "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d5",
  "is_active": true
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Team updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "name": "Strikers United",
    "code": "STU",
    "image_url": "https://example.com/logos/strikers_united.png",
    "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d5",
    "is_active": true
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updateTeam({
  required String teamId,
  String? name,
  String? code,
  String? imageUrl,
  String? captainId,
  String? viceCaptainId,
  bool? isActive,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (name != null) 'name': name,
      if (code != null) 'code': code,
      if (imageUrl != null) 'image_url': imageUrl,
      if (captainId != null) 'captain_id': captainId,
      if (viceCaptainId != null) 'vice_captain_id': viceCaptainId,
      if (isActive != null) 'is_active': isActive,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `DELETE /teams/{team_id}`
Delete a team by ID.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:delete`
- **Access:** Admin only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Team deleted successfully",
  "data": null
}
```

#### Flutter Example — Admin View
```dart
Future<bool> deleteTeam(String teamId) async {
  final response = await http.delete(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  return data['success'] == true;
}
```

---

### `PUT /teams/{team_id}/leadership`
Update team captain and/or vice-captain. Both users must already be current members of this team (`user.team_id == team_id`).

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:update`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d2"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "team leadership updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "name": "Strikers XI",
    "code": "STK",
    "image_url": "https://example.com/logos/strikers.png",
    "captain_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "vice_captain_id": "64f1a2b3c4d5e6f7a8b9c0d2",
    "initial_balance": 6250,
    "balance": 5250,
    "is_active": true,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updateTeamLeadership({
  required String teamId,
  String? captainId,
  String? viceCaptainId,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId/leadership'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (captainId != null) 'captain_id': captainId,
      if (viceCaptainId != null) 'vice_captain_id': viceCaptainId,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /teams/{team_id}/members`
Fetch all players and members assigned to a team.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "team members fetched successfully",
  "data": {
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "team_name": "Strikers XI",
    "members": [
      {
        "id": "64f1a2b3c4d5e6f7a8b9c0d1",
        "name": "Rahul Kumar Sharma",
        "first_name": "Rahul",
        "middle_name": "Kumar",
        "last_name": "Sharma",
        "roll_no": "CS202601",
        "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
        "email": "rahul.sharma@bhaktipurv.com",
        "mobile": "+919876543210",
        "image_url": "https://example.com/avatar.jpg",
        "is_active": true,
        "is_allowed": true,
        "is_superuser": false
      }
    ]
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> getTeamMembers(String teamId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId/members'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /teams/{team_id}/wallet`
Fetch team wallet summary including initial budget, current available balance, total spent, total refunded, and total transaction count.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Team wallet summary fetched successfully",
  "data": {
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "team_name": "Strikers XI",
    "initial_balance": 6250,
    "balance": 5250,
    "total_spent": 1000,
    "total_refunded": 0,
    "total_transactions": 1
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> getTeamWallet(String teamId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId/wallet'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /teams/{team_id}/transactions`
Fetch paginated wallet transaction ledger history for a team.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | `int` | `0` | Number of transaction records to skip |
| `limit` | `int` | `50` | Maximum number of records to return (1-100) |

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Team transactions fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c7a1",
      "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
      "transaction_type": "AUCTION_PURCHASE",
      "amount": -1000,
      "balance_before": 6250,
      "balance_after": 5250,
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "description": "Purchased Rahul Kumar Sharma for 1000 Pushp",
      "created_by": "64f1a2b3c4d5e6f7a8b9c0d9",
      "created_at": "2026-09-04T12:00:00Z"
    }
  ]
}
```

#### Flutter Example (Android & Web)
```dart
Future<List<dynamic>> getTeamTransactions({
  required String teamId,
  int skip = 0,
  int limit = 50,
}) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId/transactions?skip=$skip&limit=$limit'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `POST /teams/{team_id}/wallet/adjust`
Manually credit or debit team wallet balance with an audit reason.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:update`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "amount": 500,
  "description": "Bonus Pushp for fair play award"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Team wallet adjusted successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c7a2",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "transaction_type": "MANUAL_ADJUSTMENT",
    "amount": 500,
    "balance_before": 5250,
    "balance_after": 5750,
    "description": "Bonus Pushp for fair play award",
    "created_at": "2026-09-04T12:30:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> adjustTeamWallet({
  required String teamId,
  required int amount,
  required String description,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId/wallet/adjust'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'amount': amount,
      'description': description,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `POST /teams/{team_id}/members/{user_id}`
Assign / purchase a player for a team at auction. Debits the player's purchase price from the team wallet balance and updates player's current `team_id` and `team_price`.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:update`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "price": 1000
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "player assigned successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "first_name": "Rahul",
    "middle_name": "Kumar",
    "last_name": "Sharma",
    "roll_no": "CS202601",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "email": "rahul.sharma@bhaktipurv.com",
    "mobile": "+919876543210",
    "image_url": "https://example.com/avatar.jpg",
    "is_active": true,
    "is_allowed": true,
    "is_superuser": false
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> assignPlayerToTeam({
  required String teamId,
  required String userId,
  required int price,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId/members/$userId'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({'price': price}),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `DELETE /teams/{team_id}/members/{user_id}`
Remove a player from a team. Refunds the player's purchase price back into the team wallet, clears captaincy if held, and removes team association.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:update`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "player removed successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "first_name": "Rahul",
    "middle_name": "Kumar",
    "last_name": "Sharma",
    "roll_no": "CS202601",
    "team_id": null,
    "email": "rahul.sharma@bhaktipurv.com",
    "mobile": "+919876543210",
    "image_url": "https://example.com/avatar.jpg",
    "is_active": true,
    "is_allowed": true,
    "is_superuser": false
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> removePlayerFromTeam({
  required String teamId,
  required String userId,
}) async {
  final response = await http.delete(
    Uri.parse('${ApiClient.baseUrl}/teams/$teamId/members/$userId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `POST /teams/{destination_team_id}/members/{user_id}/transfer`
Transfer a player from their current team (`source_team_id`) to a new destination team. Debits the destination team wallet and refunds the source team wallet.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:update`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "source_team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
  "price": 1200
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "player transferred successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "name": "Rahul Kumar Sharma",
    "first_name": "Rahul",
    "middle_name": "Kumar",
    "last_name": "Sharma",
    "roll_no": "CS202601",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b2",
    "email": "rahul.sharma@bhaktipurv.com",
    "mobile": "+919876543210",
    "image_url": "https://example.com/avatar.jpg",
    "is_active": true,
    "is_allowed": true,
    "is_superuser": false
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> transferPlayer({
  required String destinationTeamId,
  required String userId,
  required String sourceTeamId,
  int? price,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/teams/$destinationTeamId/members/$userId/transfer'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'source_team_id': sourceTeamId,
      if (price != null) 'price': price,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

## 8. Team Assignments

Base Route: `/team-assignments`

Handles individual player team assignments, transfers, and complete historical audit records of player movements across teams.

---

### `POST /team-assignments`
Assign a user to a team.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:assign`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
  "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
  "price": 1000
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User assigned to team successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c8a1",
    "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "price": 1000,
    "is_current": true
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> createTeamAssignment({
  required String userId,
  required String teamId,
  int price = 0,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/team-assignments'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'user_id': userId,
      'team_id': teamId,
      'price': price,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `POST /team-assignments/{user_id}/transfer`
Transfer a user from their current team to a new team.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:assign`
- **Access:** Admin / Privileged User only

#### Request Body
```json
{
  "new_team_id": "64f1a2b3c4d5e6f7a8b9c2b2",
  "price": 1200
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User transferred successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c8a2",
    "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b2",
    "price": 1200,
    "is_current": true
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> transferUserAssignment({
  required String userId,
  required String newTeamId,
  int? price,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/team-assignments/$userId/transfer'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'new_team_id': newTeamId,
      if (price != null) 'price': price,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `DELETE /team-assignments/{user_id}`
Remove a user from their current team assignment.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:assign`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User removed from team successfully",
  "data": null
}
```

#### Flutter Example — Admin View
```dart
Future<bool> removeUserAssignment(String userId) async {
  final response = await http.delete(
    Uri.parse('${ApiClient.baseUrl}/team-assignments/$userId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  return data['success'] == true;
}
```

---

### `GET /team-assignments/user/{user_id}`
Fetch the active team assignment for a user.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User team fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c8a1",
    "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
    "price": 1000,
    "assigned_at": "2026-09-04T12:00:00Z"
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> getUserAssignment(String userId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/team-assignments/user/$userId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /team-assignments/team/{team_id}`
Fetch all current member assignments for a team.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Team members fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c8a1",
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
      "price": 1000,
      "assigned_at": "2026-09-04T12:00:00Z"
    }
  ]
}
```

#### Flutter Example (Android & Web)
```dart
Future<List<dynamic>> getTeamAssignments(String teamId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/team-assignments/team/$teamId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `GET /team-assignments/user/{user_id}/history`
Fetch complete assignment history of a user across all teams.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `team:view`
- **Access:** All authenticated users

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "User team history fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c8a1",
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "team_id": "64f1a2b3c4d5e6f7a8b9c2b1",
      "price": 1000,
      "assigned_at": "2026-09-04T10:00:00Z",
      "assigned_by": "64f1a2b3c4d5e6f7a8b9c0d9",
      "removed_at": "2026-09-04T12:00:00Z",
      "removed_by": "64f1a2b3c4d5e6f7a8b9c0d9",
      "is_current": false
    },
    {
      "id": "64f1a2b3c4d5e6f7a8b9c8a2",
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "team_id": "64f1a2b3c4d5e6f7a8b9c2b2",
      "price": 1200,
      "assigned_at": "2026-09-04T12:00:00Z",
      "assigned_by": "64f1a2b3c4d5e6f7a8b9c0d9",
      "removed_at": null,
      "removed_by": null,
      "is_current": true
    }
  ]
}
```

#### Flutter Example (Android & Web)
```dart
Future<List<dynamic>> getUserAssignmentHistory(String userId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/team-assignments/user/$userId/history'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

## 9. App Configuration

Base Route: `/app-config`

---

### `GET /app-config/public`
Fetch public application runtime configuration (recommended for app startup before login). Does not expose internal document ID or audit metadata.

- **Authorization:** None Required
- **Access:** Public (called on app startup / splash screen)

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "App configuration fetched successfully",
  "data": {
    "maintenance_mode": false,
    "maintenance_message": null,
    "minimum_version": "1.0.0",
    "latest_version": "1.2.0",
    "update_message": "A new version of the app is available. Please update.",
    "registration_open": true,
    "android_store_url": "https://play.google.com/store/apps/details?id=com.bhaktipurv.app"
  }
}
```

#### Flutter Example — App Startup Check (Android & Web)
```dart
Future<Map<String, dynamic>> getPublicAppConfig() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/app-config/public'),
    headers: await ApiClient.headers(),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /app-config`
Fetch full application runtime configuration including system metadata and audit details.

- **Authorization:** None Required
- **Access:** Public

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "App configuration fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c3c1",
    "maintenance_mode": false,
    "maintenance_message": null,
    "minimum_version": "1.0.0",
    "latest_version": "1.2.0",
    "update_message": "A new version of the app is available. Please update.",
    "registration_open": true,
    "android_store_url": "https://play.google.com/store/apps/details?id=com.bhaktipurv.app",
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-01T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example — Normal User (startup check)
```dart
Future<Map<String, dynamic>> getAppConfig() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/app-config'),
    headers: await ApiClient.headers(),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

#### Flutter Example — Android version check
```dart
Future<void> runStartupChecks(String currentVersion) async {
  final config = await getPublicAppConfig();
  if (config['maintenance_mode'] == true) {
    // Navigate to MaintenanceScreen with config['maintenance_message']
    return;
  }
  // Check registration status: config['registration_open']
  // Compare currentVersion with config['minimum_version']
  // If outdated: open config['android_store_url'] via url_launcher
}
```

#### Flutter Example — Web maintenance check
```dart
Future<void> runWebStartupCheck() async {
  final config = await getPublicAppConfig();
  if (config['maintenance_mode'] == true) {
    // Show full-page maintenance overlay
  }
}
```

---

### `POST /app-config`
Create initial application configuration.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `appconfig:create`
- **Access:** Admin / Superuser only

#### Request Body
```json
{
  "maintenance_mode": false,
  "maintenance_message": "Scheduled maintenance from 2 AM to 4 AM IST",
  "minimum_version": "1.0.0",
  "latest_version": "1.2.0",
  "update_message": "Please update to the latest version for improved security.",
  "registration_open": true,
  "android_store_url": "https://play.google.com/store/apps/details?id=com.bhaktipurv.app"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 201,
  "message": "App configuration created successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c3c1",
    "maintenance_mode": false,
    "maintenance_message": "Scheduled maintenance from 2 AM to 4 AM IST",
    "minimum_version": "1.0.0",
    "latest_version": "1.2.0",
    "update_message": "Please update to the latest version for improved security.",
    "registration_open": true,
    "android_store_url": "https://play.google.com/store/apps/details?id=com.bhaktipurv.app",
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-01T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> createAppConfig({
  required bool maintenanceMode,
  String? maintenanceMessage,
  required String minimumVersion,
  required String latestVersion,
  String? updateMessage,
  bool registrationOpen = true,
  required String androidStoreUrl,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/app-config'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'maintenance_mode': maintenanceMode,
      'maintenance_message': maintenanceMessage,
      'minimum_version': minimumVersion,
      'latest_version': latestVersion,
      'update_message': updateMessage,
      'registration_open': registrationOpen,
      'android_store_url': androidStoreUrl,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /app-config`
Update application configuration settings.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `appconfig:update`
- **Access:** Admin / Superuser only

#### Request Body
```json
{
  "maintenance_mode": true,
  "maintenance_message": "System is under maintenance. Please check back in 30 minutes.",
  "minimum_version": "1.1.0",
  "latest_version": "1.3.0",
  "update_message": "Critical security update available. Please update immediately.",
  "registration_open": false,
  "android_store_url": "https://play.google.com/store/apps/details?id=com.bhaktipurv.app"
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "App configuration updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c3c1",
    "maintenance_mode": true,
    "maintenance_message": "System is under maintenance. Please check back in 30 minutes.",
    "minimum_version": "1.1.0",
    "latest_version": "1.3.0",
    "update_message": "Critical security update available. Please update immediately.",
    "registration_open": false,
    "android_store_url": "https://play.google.com/store/apps/details?id=com.bhaktipurv.app",
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-01T18:30:00Z",
    "updated_at": "2026-09-03T19:00:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updateAppConfig({
  bool? maintenanceMode,
  String? maintenanceMessage,
  String? minimumVersion,
  String? latestVersion,
  String? updateMessage,
  bool? registrationOpen,
  String? androidStoreUrl,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/app-config'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (maintenanceMode != null) 'maintenance_mode': maintenanceMode,
      if (maintenanceMessage != null) 'maintenance_message': maintenanceMessage,
      if (minimumVersion != null) 'minimum_version': minimumVersion,
      if (latestVersion != null) 'latest_version': latestVersion,
      if (updateMessage != null) 'update_message': updateMessage,
      if (registrationOpen != null) 'registration_open': registrationOpen,
      if (androidStoreUrl != null) 'android_store_url': androidStoreUrl,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

## 10. Session Management

Base Route: `/sessions`

---

### `GET /sessions/history`
Fetch login history for the currently authenticated user.

- **Authorization:** `Bearer <access_token>`
- **Access:** All authenticated users (own sessions only)

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Login history fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c4d1",
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "device_id": "android-uuid-abc123",
      "device_name": "Samsung Galaxy S24",
      "platform": "android",
      "is_active": true,
      "login_at": "2026-09-03T10:00:00Z",
      "logout_at": null,
      "invalidated_at": null,
      "invalidated_reason": null
    },
    {
      "id": "64f1a2b3c4d5e6f7a8b9c4d2",
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "device_id": "web-session-1725357000000",
      "device_name": "Flutter Web Browser",
      "platform": "web",
      "is_active": false,
      "login_at": "2026-09-02T08:00:00Z",
      "logout_at": "2026-09-02T17:00:00Z",
      "invalidated_at": null,
      "invalidated_reason": null
    }
  ]
}
```

#### Flutter Example — Normal User View
```dart
Future<List<dynamic>> getMySessionHistory() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/sessions/history'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `GET /sessions/history/{user_id}`
Fetch login session history for a specific user.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `sessions:view`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Login history fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c4d3",
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d2",
      "device_id": "android-uuid-xyz789",
      "device_name": "OnePlus 12",
      "platform": "android",
      "is_active": false,
      "login_at": "2026-09-01T10:00:00Z",
      "logout_at": "2026-09-01T18:00:00Z",
      "invalidated_at": null,
      "invalidated_reason": null
    }
  ]
}
```

#### Flutter Example — Admin View
```dart
Future<List<dynamic>> getUserSessionHistory(String userId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/sessions/history/$userId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

## 11. Registration Management

Base Route: `/registration`

Handles participant sports registration and event participation details, including T-shirt sizes, individual sports proficiency levels, personal talent notes, and contribution ratings for group talent and Q&A sessions.

---

### Enums & Data Types

#### `TshirtSize`
| Value | Description |
|-------|-------------|
| `"XS"` | Extra Small |
| `"S"` | Small |
| `"M"` | Medium |
| `"L"` | Large |
| `"XL"` | Extra Large |
| `"XXL"` | Double Extra Large |
| `"XXXL"` | Triple Extra Large |

#### `SportLevel`
| Value | Description |
|-------|-------------|
| `"expert"` | Expert proficiency |
| `"intermediate"` | Intermediate proficiency |
| `"beginner"` | Beginner proficiency |
| `"no"` | Does not play / Not interested |

---

### `POST /registration`
Submit sports and event participation registration for the authenticated user. Each user may only submit registration once; subsequent submissions return a 409 Conflict.

- **Authorization:** `Bearer <access_token>`
- **Access:** All authenticated users (once per user)

#### Request Body
```json
{
  "tshirt_size": "L",
  "cricket": "intermediate",
  "volleyball": "beginner",
  "kabaddi": "no",
  "kho_kho": "beginner",
  "foosball": "expert",
  "frisbee": "intermediate",
  "dodge_ball": "beginner",
  "chess": "expert",
  "carrom": "intermediate",
  "tennis": "beginner",
  "single_talent": "Singing and Playing Acoustic Guitar",
  "group_talent_contribution": 80,
  "qna_contribution": 50
}
```

#### Field Specifications
| Field | Type | Required | Constraints / Values | Description |
|-------|------|----------|----------------------|-------------|
| `tshirt_size` | `string` | Yes | `"XS"`, `"S"`, `"M"`, `"L"`, `"XL"`, `"XXL"`, `"XXXL"` | Participant T-shirt size |
| `cricket` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Cricket skill level |
| `volleyball` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Volleyball skill level |
| `kabaddi` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Kabaddi skill level |
| `kho_kho` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Kho-Kho skill level |
| `foosball` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Foosball skill level |
| `frisbee` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Frisbee skill level |
| `dodge_ball` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Dodgeball skill level |
| `chess` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Chess skill level |
| `carrom` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Carrom skill level |
| `tennis` | `string` | Yes | `"expert"`, `"intermediate"`, `"beginner"`, `"no"` | Tennis skill level |
| `single_talent` | `string \| null` | No | Max 500 characters | Individual performance or talent description |
| `group_talent_contribution` | `int` | Yes | 0 to 100 | Percentage readiness / contribution to group talent |
| `qna_contribution` | `int` | Yes | 0 to 100 | Percentage readiness / contribution to Q&A sessions |

#### Response Example
```json
{
  "success": true,
  "code": 201,
  "message": "Registration completed successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c5e1",
    "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "tshirt_size": "L",
    "cricket": "intermediate",
    "volleyball": "beginner",
    "kabaddi": "no",
    "kho_kho": "beginner",
    "foosball": "expert",
    "frisbee": "intermediate",
    "dodge_ball": "beginner",
    "chess": "expert",
    "carrom": "intermediate",
    "tennis": "beginner",
    "single_talent": "Singing and Playing Acoustic Guitar",
    "group_talent_contribution": 80,
    "qna_contribution": 50,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example (Android & Web)
```dart
Future<Map<String, dynamic>> submitRegistration({
  required String tshirtSize,
  required String cricket,
  required String volleyball,
  required String kabaddi,
  required String khoKho,
  required String foosball,
  required String frisbee,
  required String dodgeBall,
  required String chess,
  required String carrom,
  required String tennis,
  String? singleTalent,
  required int groupTalentContribution,
  required int qnaContribution,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/registration'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'tshirt_size': tshirtSize,
      'cricket': cricket,
      'volleyball': volleyball,
      'kabaddi': kabaddi,
      'kho_kho': khoKho,
      'foosball': foosball,
      'frisbee': frisbee,
      'dodge_ball': dodgeBall,
      'chess': chess,
      'carrom': carrom,
      'tennis': tennis,
      'single_talent': singleTalent,
      'group_talent_contribution': groupTalentContribution,
      'qna_contribution': qnaContribution,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /registration/me`
Fetch sports registration record for the currently authenticated user.

- **Authorization:** `Bearer <access_token>`
- **Access:** All authenticated users (own registration)

#### Request Body
None

#### Response Example (Registered)
```json
{
  "success": true,
  "code": 200,
  "message": "Registration fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c5e1",
    "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "tshirt_size": "L",
    "cricket": "intermediate",
    "volleyball": "beginner",
    "kabaddi": "no",
    "kho_kho": "beginner",
    "foosball": "expert",
    "frisbee": "intermediate",
    "dodge_ball": "beginner",
    "chess": "expert",
    "carrom": "intermediate",
    "tennis": "beginner",
    "single_talent": "Singing and Playing Acoustic Guitar",
    "group_talent_contribution": 80,
    "qna_contribution": 50,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Response Example (Not Registered Yet)
```json
{
  "success": true,
  "code": 200,
  "message": "Registration fetched successfully",
  "data": null
}
```

#### Flutter Example — Normal User View
```dart
Future<Map<String, dynamic>?> getMyRegistration() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/registration/me'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `GET /registration/all`
Fetch all submitted participant registrations across the platform.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `registration:view`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Registration fetched successfully",
  "data": [
    {
      "id": "64f1a2b3c4d5e6f7a8b9c5e1",
      "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
      "tshirt_size": "L",
      "cricket": "intermediate",
      "volleyball": "beginner",
      "kabaddi": "no",
      "kho_kho": "beginner",
      "foosball": "expert",
      "frisbee": "intermediate",
      "dodge_ball": "beginner",
      "chess": "expert",
      "carrom": "intermediate",
      "tennis": "beginner",
      "single_talent": "Singing and Playing Acoustic Guitar",
      "group_talent_contribution": 80,
      "qna_contribution": 50,
      "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
      "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
      "created_at": "2026-09-03T18:30:00Z",
      "updated_at": "2026-09-03T18:30:00Z"
    }
  ]
}
```

#### Flutter Example — Admin View
```dart
Future<List<dynamic>> getAllRegistrations() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/registration/all'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'] as List;
  throw Exception(data['message']);
}
```

---

### `GET /registration/{registration_id}`
Fetch a single participant registration by its document ID.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `registration:view`
- **Access:** Admin / Privileged User only

#### Request Body
None

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Registration fetched successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c5e1",
    "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "tshirt_size": "L",
    "cricket": "intermediate",
    "volleyball": "beginner",
    "kabaddi": "no",
    "kho_kho": "beginner",
    "foosball": "expert",
    "frisbee": "intermediate",
    "dodge_ball": "beginner",
    "chess": "expert",
    "carrom": "intermediate",
    "tennis": "beginner",
    "single_talent": "Singing and Playing Acoustic Guitar",
    "group_talent_contribution": 80,
    "qna_contribution": 50,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z",
    "updated_at": "2026-09-03T18:30:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> getRegistrationById(String registrationId) async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/registration/$registrationId'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

### `PUT /registration/{registration_id}`
Update an existing participant registration record.

- **Authorization:** `Bearer <access_token>`
- **Required Permission:** `registration:update`
- **Access:** Admin / Privileged User only

#### Request Body
All fields are optional; provide only the fields to update:
```json
{
  "tshirt_size": "XL",
  "cricket": "expert",
  "single_talent": "Standup Comedy and Mimicry",
  "group_talent_contribution": 90,
  "qna_contribution": 60
}
```

#### Response Example
```json
{
  "success": true,
  "code": 200,
  "message": "Registration updated successfully",
  "data": {
    "id": "64f1a2b3c4d5e6f7a8b9c5e1",
    "user_id": "64f1a2b3c4d5e6f7a8b9c0d1",
    "tshirt_size": "XL",
    "cricket": "expert",
    "volleyball": "beginner",
    "kabaddi": "no",
    "kho_kho": "beginner",
    "foosball": "expert",
    "frisbee": "intermediate",
    "dodge_ball": "beginner",
    "chess": "expert",
    "carrom": "intermediate",
    "tennis": "beginner",
    "single_talent": "Standup Comedy and Mimicry",
    "group_talent_contribution": 90,
    "qna_contribution": 60,
    "created_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "updated_by": "64f1a2b3c4d5e6f7a8b9c0d1",
    "created_at": "2026-09-03T18:30:00Z",
    "updated_at": "2026-09-03T19:00:00Z"
  }
}
```

#### Flutter Example — Admin View
```dart
Future<Map<String, dynamic>> updateRegistration({
  required String registrationId,
  String? tshirtSize,
  String? cricket,
  String? volleyball,
  String? kabaddi,
  String? khoKho,
  String? foosball,
  String? frisbee,
  String? dodgeBall,
  String? chess,
  String? carrom,
  String? tennis,
  String? singleTalent,
  int? groupTalentContribution,
  int? qnaContribution,
}) async {
  final response = await http.put(
    Uri.parse('${ApiClient.baseUrl}/registration/$registrationId'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (tshirtSize != null) 'tshirt_size': tshirtSize,
      if (cricket != null) 'cricket': cricket,
      if (volleyball != null) 'volleyball': volleyball,
      if (kabaddi != null) 'kabaddi': kabaddi,
      if (khoKho != null) 'kho_kho': khoKho,
      if (foosball != null) 'foosball': foosball,
      if (frisbee != null) 'frisbee': frisbee,
      if (dodgeBall != null) 'dodge_ball': dodgeBall,
      if (chess != null) 'chess': chess,
      if (carrom != null) 'carrom': carrom,
      if (tennis != null) 'tennis': tennis,
      if (singleTalent != null) 'single_talent': singleTalent,
      if (groupTalentContribution != null) 'group_talent_contribution': groupTalentContribution,
      if (qnaContribution != null) 'qna_contribution': qnaContribution,
    }),
  );
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data['data'];
  throw Exception(data['message']);
}
```

---

## 12. Auction Management

Base Route: `/auction`

> **Real-time Live Auction & Spectator Screen APIs**
> - **Public Screen APIs (No Auth Required):** Allows spectators, projector screens, and public web clients to view live bids, team budgets, and player history in real time.
> - **WebSocket Stream (`/auction/ws`):** Provides instant push notifications whenever a bid is placed, rolled back, player is sold/unsold, or session state changes.
> - **Admin Controls:** Strictly protected (`is_superuser = true`) to manage sessions, advance players, place bids, roll back bids, and finalize sales.

---

### Currency & Bid Ladder

The auction uses a **Pushp** currency system denominated in **Maroon (M)**, **Saffron (S)**, and **Purple (P)**:

| Unit | Value in Maroon (M) | Display Example |
| :--- | :--- | :--- |
| **Maroon (M)** | 1 M | `10 M` |
| **Saffron (S)** | 25 M | `1 S` (= 25 M) |
| **Purple (P)** | 625 M (25 S) | `1 P` (= 25 S = 625 M) |

Combined display format: `1 P + 2 S + 10 M`

#### Predefined Bid Ladder (`BID_LADDER`)
`[5, 10, 15, 20, 25, 50, 75, 100, 125, 175, 225, 275, 325, 425, 525, 625, 750, 875, 1000, 1150, 1300, 1450, 1600, 1800, 2000, 2500, 3125, 3750, 4375, 5000]`

---

### `WS /auction/ws`
Public real-time WebSocket connection.

- **Authorization:** None Required (Public)
- **Protocol:** `ws://` / `wss://`

#### Broadcast Event Types (`event`)

| Event Name | Description | Payload Data Sample |
| :--- | :--- | :--- |
| `auction:session_started` | Session started | `{"session_id": "...", "status": "live", "remaining_count": 50}` |
| `auction:player_started` | Player brought up for auction | `{"auction_id": "...", "user_id": "...", "name": "...", "roll_no": "...", "base_price": 25}` |
| `auction:bid` | New valid bid placed | `{"auction_id": "...", "team_id": "...", "team_name": "...", "team_code": "...", "amount": 50, "amount_display": "2 S"}` |
| `auction:bid_rollback` | Accidental bid rolled back | `{"auction_id": "...", "current_bid": 25, "current_bid_display": "1 S", "current_team_id": null}` |
| `auction:player_sold` | Player sold to winning team | `{"auction_id": "...", "user_id": "...", "player_name": "...", "team_name": "...", "amount": 50, "amount_display": "2 S"}` |
| `auction:player_unsold` | Player marked unsold | `{"auction_id": "...", "user_id": "..."}` |
| `auction:paused` | Session paused | `{"session_id": "...", "status": "paused"}` |
| `auction:resumed` | Session resumed | `{"session_id": "...", "status": "live"}` |
| `auction:ended` | Session ended | `{"session_id": "...", "status": "ended"}` |

#### Flutter WebSocket Example (Web & Mobile)
```dart
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class AuctionWebSocketService {
  WebSocketChannel? _channel;

  void connect({required Function(String event, dynamic data) onEvent}) {
    final wsUrl = Uri.parse('wss://api.bhaktipurv.com/auction/ws');
    _channel = WebSocketChannel.connect(wsUrl);

    _channel!.stream.listen((message) {
      final decoded = jsonDecode(message);
      final event = decoded['event'] as String;
      final data = decoded['data'];
      onEvent(event, data);
    }, onError: (err) {
      print('WebSocket error: $err');
    }, onDone: () {
      print('WebSocket disconnected');
    });
  }

  void disconnect() {
    _channel?.sink.close();
  }
}
```

---

### `GET /auction/public/live`
Public live auction state for big screens, projector displays, and spectators.

- **Authorization:** None Required (Public)
- **Access:** Public

#### Request Body
None

#### Response Example (When Player is Live)
```json
{
  "session": {
    "id": "66e2c34a980b12f4d1e20a01",
    "status": "live",
    "remaining_count": 42,
    "unsold_count": 3,
    "started_at": "2026-09-12T08:30:00Z"
  },
  "player": {
    "id": "66e2c34a980b12f4d1e20b02",
    "name": "Aakash Patel",
    "roll_no": "CS202605",
    "image_url": "https://example.com/players/aakash.jpg",
    "base_price": 25,
    "base_price_display": "1 S"
  },
  "current_bid": 75,
  "current_bid_display": "3 S",
  "current_team": {
    "id": "66e2c34a980b12f4d1e20c03",
    "name": "Chennai Kings",
    "code": "CSK",
    "image_url": "https://example.com/teams/csk.png"
  },
  "status": "live",
  "timer": 15,
  "recent_bids": [
    {
      "id": "66e2c34a980b12f4d1e20d04",
      "team_id": "66e2c34a980b12f4d1e20c03",
      "team_name": "Chennai Kings",
      "team_code": "CSK",
      "team_image_url": "https://example.com/teams/csk.png",
      "amount": 75,
      "amount_display": "3 S",
      "created_at": "2026-09-12T08:31:10Z"
    },
    {
      "id": "66e2c34a980b12f4d1e20d03",
      "team_id": "66e2c34a980b12f4d1e20c02",
      "team_name": "Mumbai Stars",
      "team_code": "MI",
      "team_image_url": "https://example.com/teams/mi.png",
      "amount": 50,
      "amount_display": "2 S",
      "created_at": "2026-09-12T08:30:45Z"
    }
  ]
}
```

#### Flutter Example (Public Screen)
```dart
Future<Map<String, dynamic>> getPublicLiveAuction() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/auction/public/live'),
  );
  return jsonDecode(response.body);
}
```

---

### `GET /auction/public/teams`
Public team standings, remaining budget, and acquired squad rosters.

- **Authorization:** None Required (Public)
- **Access:** Public

#### Request Body
None

#### Response Example
```json
[
  {
    "id": "66e2c34a980b12f4d1e20c03",
    "name": "Chennai Kings",
    "code": "CSK",
    "image_url": "https://example.com/teams/csk.png",
    "initial_balance": 6250,
    "initial_balance_display": "10 P",
    "balance": 5500,
    "balance_display": "8 P + 20 S",
    "players_count": 2,
    "players": [
      {
        "id": "66e2c34a980b12f4d1e20b01",
        "name": "Rahul Sharma",
        "roll_no": "CS202601",
        "price": 500,
        "price_display": "20 S",
        "image_url": "https://example.com/players/rahul.jpg"
      },
      {
        "id": "66e2c34a980b12f4d1e20b02",
        "name": "Aakash Patel",
        "roll_no": "CS202605",
        "price": 250,
        "price_display": "10 S",
        "image_url": "https://example.com/players/aakash.jpg"
      }
    ]
  }
]
```

#### Flutter Example
```dart
Future<List<dynamic>> getPublicTeams() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/auction/public/teams'),
  );
  return jsonDecode(response.body) as List;
}
```

---

### `GET /auction/public/recent`
Public list of recently auctioned players (sold and unsold).

- **Authorization:** None Required (Public)
- **Access:** Public

#### Request Body
None

#### Response Example
```json
[
  {
    "auction_id": "66e2c34a980b12f4d1e20e01",
    "player_id": "66e2c34a980b12f4d1e20b01",
    "player_name": "Rahul Sharma",
    "roll_no": "CS202601",
    "image_url": "https://example.com/players/rahul.jpg",
    "base_price": 25,
    "base_price_display": "1 S",
    "status": "sold",
    "final_price": 500,
    "final_price_display": "20 S",
    "winning_team_id": "66e2c34a980b12f4d1e20c03",
    "winning_team_name": "Chennai Kings",
    "winning_team_code": "CSK",
    "ended_at": "2026-09-12T08:25:00Z"
  },
  {
    "auction_id": "66e2c34a980b12f4d1e20e02",
    "player_id": "66e2c34a980b12f4d1e20b08",
    "player_name": "Vikram Singh",
    "roll_no": "ME202611",
    "image_url": null,
    "base_price": 25,
    "base_price_display": "1 S",
    "status": "unsold",
    "final_price": null,
    "final_price_display": null,
    "winning_team_id": null,
    "winning_team_name": null,
    "winning_team_code": null,
    "ended_at": "2026-09-12T08:20:00Z"
  }
]
```

#### Flutter Example
```dart
Future<List<dynamic>> getPublicRecentActivity() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/auction/public/recent'),
  );
  return jsonDecode(response.body) as List;
}
```

---

### `POST /auction/start`
Start a new live auction session. Prepares registered, active, unassigned players into the bidding queue.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
```json
{
  "sort_by": "base_price",
  "sort_direction": "asc"
}
```
*Sort options:* `sort_by` can be `"base_price"`, `"roll_no"`, or `"name"`. `sort_direction` can be `"asc"` or `"desc"`.

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20a01",
  "status": "live",
  "sort_by": "base_price",
  "sort_direction": "asc",
  "remaining_count": 45,
  "unsold_count": 0,
  "current_user_id": null,
  "current_auction_id": null,
  "started_at": "2026-09-12T08:30:00Z",
  "paused_at": null,
  "ended_at": null
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> startAuctionSession({
  String sortBy = 'base_price',
  String sortDirection = 'asc',
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/start'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'sort_by': sortBy,
      'sort_direction': sortDirection,
    }),
  );
  final data = jsonDecode(response.body);
  if (response.statusCode == 201) return data;
  throw Exception(data['detail'] ?? 'Failed to start auction');
}
```

---

### `GET /auction/session/current`
Get details of the currently active/paused auction session.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
None

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20a01",
  "status": "live",
  "sort_by": "base_price",
  "sort_direction": "asc",
  "remaining_count": 44,
  "unsold_count": 1,
  "current_user_id": "66e2c34a980b12f4d1e20b02",
  "current_auction_id": "66e2c34a980b12f4d1e20e03",
  "started_at": "2026-09-12T08:30:00Z",
  "paused_at": null,
  "ended_at": null
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> getCurrentAuctionSession() async {
  final response = await http.get(
    Uri.parse('${ApiClient.baseUrl}/auction/session/current'),
    headers: await ApiClient.headers(auth: true),
  );
  return jsonDecode(response.body);
}
```

---

### `POST /auction/session/{session_id}/next`
Advance to the next player in the auction queue.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
None

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20e03",
  "user_id": "66e2c34a980b12f4d1e20b02",
  "base_price": 25,
  "base_price_display": "1 S",
  "status": "live",
  "current_bid": 25,
  "current_bid_display": "1 S",
  "current_team_id": null,
  "started_at": "2026-09-12T08:35:00Z",
  "ended_at": null
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>?> nextPlayer(String sessionId) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/session/$sessionId/next'),
    headers: await ApiClient.headers(auth: true),
  );
  if (response.statusCode == 200) {
    return response.body.isNotEmpty ? jsonDecode(response.body) : null;
  }
  throw Exception(jsonDecode(response.body)['detail']);
}
```

---

### `POST /auction/{auction_id}/bid`
Place a bid on behalf of a team according to the bid ladder.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
```json
{
  "team_id": "66e2c34a980b12f4d1e20c03",
  "amount": 50
}
```

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20d05",
  "auction_id": "66e2c34a980b12f4d1e20e03",
  "team_id": "66e2c34a980b12f4d1e20c03",
  "user_id": "66e2c34a980b12f4d1e20b02",
  "amount": 50,
  "amount_display": "2 S",
  "created_at": "2026-09-12T08:36:12Z"
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> placeBid({
  required String auctionId,
  required String teamId,
  required int amount,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/$auctionId/bid'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      'team_id': teamId,
      'amount': amount,
    }),
  );
  final data = jsonDecode(response.body);
  if (response.statusCode == 200) return data;
  throw Exception(data['detail'] ?? 'Bid placement failed');
}
```

---

### `POST /auction/{auction_id}/rollback-bid`
Roll back the latest active bid on the current auction attempt (reverts to previous bid or base price).

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
None

#### Response Example
```json
{
  "auction_id": "66e2c34a980b12f4d1e20e03",
  "status": "live",
  "current_bid": 25,
  "current_bid_display": "1 S",
  "current_team_id": null,
  "rolled_back_bid_id": "66e2c34a980b12f4d1e20d05",
  "rolled_back_amount": 50,
  "rolled_back_amount_display": "2 S"
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> rollbackBid(String auctionId) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/$auctionId/rollback-bid'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (response.statusCode == 200) return data;
  throw Exception(data['detail'] ?? 'Rollback failed');
}
```

---

### `POST /auction/{auction_id}/sell`
Finalize and sell the player to the current highest bidder. Creates `TeamAssignment` and `TeamWalletTransaction`.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
None

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20e03",
  "user_id": "66e2c34a980b12f4d1e20b02",
  "base_price": 25,
  "base_price_display": "1 S",
  "status": "sold",
  "current_bid": 75,
  "current_bid_display": "3 S",
  "current_team_id": "66e2c34a980b12f4d1e20c03",
  "started_at": "2026-09-12T08:35:00Z",
  "ended_at": "2026-09-12T08:37:30Z"
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> sellPlayer(String auctionId) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/$auctionId/sell'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (response.statusCode == 200) return data;
  throw Exception(data['detail'] ?? 'Sell failed');
}
```

---

### `POST /auction/{auction_id}/unsold`
Mark the current player unsold and push them to the unsold queue for a second round.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
None

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20e03",
  "user_id": "66e2c34a980b12f4d1e20b02",
  "base_price": 25,
  "base_price_display": "1 S",
  "status": "unsold",
  "current_bid": 25,
  "current_bid_display": "1 S",
  "current_team_id": null,
  "started_at": "2026-09-12T08:35:00Z",
  "ended_at": "2026-09-12T08:38:00Z"
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> markUnsold(String auctionId) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/$auctionId/unsold'),
    headers: await ApiClient.headers(auth: true),
  );
  final data = jsonDecode(response.body);
  if (response.statusCode == 200) return data;
  throw Exception(data['detail'] ?? 'Mark unsold failed');
}
```

---

### `POST /auction/session/{session_id}/pause`
Pause the live auction session.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
None

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20a01",
  "status": "paused",
  "sort_by": "base_price",
  "sort_direction": "asc",
  "remaining_count": 40,
  "unsold_count": 2,
  "current_user_id": "66e2c34a980b12f4d1e20b02",
  "current_auction_id": "66e2c34a980b12f4d1e20e03",
  "started_at": "2026-09-12T08:30:00Z",
  "paused_at": "2026-09-12T08:40:00Z",
  "ended_at": null
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> pauseAuction(String sessionId) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/session/$sessionId/pause'),
    headers: await ApiClient.headers(auth: true),
  );
  return jsonDecode(response.body);
}
```

---

### `POST /auction/session/{session_id}/resume`
Resume a paused auction session with optional re-sorting of remaining queue.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
```json
{
  "sort_by": "base_price",
  "sort_direction": "asc"
}
```

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20a01",
  "status": "live",
  "sort_by": "base_price",
  "sort_direction": "asc",
  "remaining_count": 40,
  "unsold_count": 2,
  "current_user_id": "66e2c34a980b12f4d1e20b02",
  "current_auction_id": "66e2c34a980b12f4d1e20e03",
  "started_at": "2026-09-12T08:30:00Z",
  "paused_at": null,
  "ended_at": null
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> resumeAuction({
  required String sessionId,
  String? sortBy,
  String? sortDirection,
}) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/session/$sessionId/resume'),
    headers: await ApiClient.headers(auth: true),
    body: jsonEncode({
      if (sortBy != null) 'sort_by': sortBy,
      if (sortDirection != null) 'sort_direction': sortDirection,
    }),
  );
  return jsonDecode(response.body);
}
```

---

### `POST /auction/session/{session_id}/end`
End the auction session.

- **Authorization:** `Bearer <access_token>`
- **Access:** Superuser only

#### Request Body
None

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20a01",
  "status": "ended",
  "sort_by": "base_price",
  "sort_direction": "asc",
  "remaining_count": 0,
  "unsold_count": 5,
  "current_user_id": null,
  "current_auction_id": null,
  "started_at": "2026-09-12T08:30:00Z",
  "paused_at": null,
  "ended_at": "2026-09-12T09:15:00Z"
}
```

#### Flutter Example (Admin)
```dart
Future<Map<String, dynamic>> endAuction(String sessionId) async {
  final response = await http.post(
    Uri.parse('${ApiClient.baseUrl}/auction/session/$sessionId/end'),
    headers: await ApiClient.headers(auth: true),
  );
  return jsonDecode(response.body);
}
```

---

### `GET /auction/{auction_id}`
Fetch auction attempt details by auction ID.

- **Authorization:** None Required / Public
- **Access:** All users

#### Response Example
```json
{
  "id": "66e2c34a980b12f4d1e20e03",
  "user_id": "66e2c34a980b12f4d1e20b02",
  "base_price": 25,
  "base_price_display": "1 S",
  "status": "sold",
  "current_bid": 75,
  "current_bid_display": "3 S",
  "current_team_id": "66e2c34a980b12f4d1e20c03",
  "started_at": "2026-09-12T08:35:00Z",
  "ended_at": "2026-09-12T08:37:30Z"
}
```

---

### `GET /auction/{auction_id}/bids`
Fetch full bids history for an auction attempt.

- **Authorization:** None Required / Public
- **Access:** All users

#### Response Example
```json
[
  {
    "id": "66e2c34a980b12f4d1e20d04",
    "auction_id": "66e2c34a980b12f4d1e20e03",
    "team_id": "66e2c34a980b12f4d1e20c03",
    "user_id": "66e2c34a980b12f4d1e20b02",
    "amount": 75,
    "amount_display": "3 S",
    "created_at": "2026-09-12T08:37:10Z"
  }
]
```

---

## 13. Error Handling

### Common Error Response Format
```json
{
  "success": false,
  "code": 401,
  "message": "Authentication required. Please login.",
  "data": null
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Resource created |
| `400` | Bad request / Validation error |
| `401` | Unauthorized - token missing or invalid |
| `403` | Forbidden - insufficient permissions |
| `404` | Resource not found |
| `409` | Conflict - resource already exists |
| `422` | Unprocessable entity - invalid body schema |
| `500` | Internal server error |

### Flutter Global Error Handler
```dart
class ApiException implements Exception {
  final int code;
  final String message;
  ApiException({required this.code, required this.message});

  @override
  String toString() => 'ApiException($code): $message';
}

Map<String, dynamic> handleResponse(http.Response response) {
  final data = jsonDecode(response.body);
  if (data['success'] == true) return data;
  throw ApiException(
    code: data['code'] ?? response.statusCode,
    message: data['message'] ?? 'Unknown error',
  );
}
```

### Auto Token Refresh on 401
```dart
Future<http.Response> requestWithRefresh(
  Future<http.Response> Function() request,
) async {
  http.Response response = await request();
  if (response.statusCode == 401) {
    await refreshToken();        // refresh stored token
    response = await request();  // retry original request
  }
  return response;
}
```

---

## 14. Platform Notes

| Feature | Android | Flutter Web |
|---------|---------|-------------|
| Token Storage | `SharedPreferences` | `SharedPreferences` (localStorage) |
| `platform` login field | `"android"` | `"web"` |
| `device_id` | Android device UUID | Browser session timestamp/fingerprint |
| `device_name` | Device model name | `"Flutter Web Browser"` |
| Store URL handling | `url_launcher` to Play Store | Open in new browser tab |
| File uploads (future) | `image_picker` + multipart | Web file picker + multipart |
| CORS | Not applicable | Configure FastAPI CORS middleware |

