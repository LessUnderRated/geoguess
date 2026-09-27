#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec4 oceanColor;
    vec4 landColor;
    vec4 highlightColor;
    vec4 gridColor;
    vec4 backgroundColor;
    vec4 rimColor;
    vec2 viewSize;
    float latitude;
    float longitude;
    float radiusPx;
};

layout(binding = 1) uniform sampler2D landMap;

void main() {
    vec2 pixel = qt_TexCoord0 * viewSize;
    vec2 centre = viewSize * 0.5;
    float radius = max(radiusPx, 1.0);
    vec2 normalXY = vec2(pixel.x - centre.x, centre.y - pixel.y) / radius;
    float rho2 = dot(normalXY, normalXY);

    if (rho2 > 1.0) {
        fragColor = backgroundColor * qt_Opacity;
        return;
    }

    float depth = sqrt(max(0.0, 1.0 - rho2));
    float lat0 = radians(latitude);
    float lon0 = radians(longitude);
    float sinLat = sin(lat0);
    float cosLat = cos(lat0);
    float lat = asin(clamp(normalXY.y * cosLat + depth * sinLat, -1.0, 1.0));
    float lon = lon0 + atan(normalXY.x, depth * cosLat - normalXY.y * sinLat);

    vec2 uv = vec2(fract((degrees(lon) + 180.0) / 360.0),
                   clamp((90.0 - degrees(lat)) / 180.0, 0.0, 1.0));
    vec4 sampleColor = texture(landMap, uv);
    float land = smoothstep(0.2, 0.8, sampleColor.a);
    float highlighted = smoothstep(0.2, 0.8, sampleColor.g) * land;

    vec3 normal = normalize(vec3(normalXY, depth));
    float light = clamp(dot(normal, normalize(vec3(-0.32, 0.42, 0.85))), 0.0, 1.0);
    float shade = mix(0.62, 1.18, light);

    vec3 ocean = oceanColor.rgb * shade;
    float coverage = smoothstep(0.15, 0.85, sampleColor.r);
    vec3 ground = mix(landColor.rgb, highlightColor.rgb, highlighted) * mix(0.78, 1.12, light);
    ground *= mix(0.34, 1.0, coverage);
    vec3 color = mix(ocean, ground, land);

    float latDeg = degrees(lat);
    float lonDeg = degrees(lon);
    float latGrid = abs(fract((latDeg + 90.0) / 30.0) - 0.5);
    float lonGrid = abs(fract((lonDeg + 180.0) / 30.0) - 0.5);
    float latWidth = max(fwidth(latDeg) * 0.55, 0.15);
    float lonWidth = max(fwidth(lonDeg) * 0.55, 0.15);
    float grid = max(1.0 - smoothstep(0.0, latWidth, latGrid * 30.0),
                     1.0 - smoothstep(0.0, lonWidth, lonGrid * 30.0));
    color = mix(color, gridColor.rgb, grid * gridColor.a * (0.35 + 0.65 * land));

    float border = smoothstep(0.25, 0.85, sampleColor.b);
    color = mix(color, rimColor.rgb, border * 0.8);

    float rim = smoothstep(0.985, 1.0, sqrt(rho2));
    color = mix(color, rimColor.rgb, rim);
    float edge = smoothstep(1.0, 0.992, sqrt(rho2));
    fragColor = vec4(color, 1.0) * qt_Opacity * edge + backgroundColor * qt_Opacity * (1.0 - edge);
}
