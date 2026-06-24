#version 430 core

in vec2 v_texcoord;
in vec4 v_color;
in vec3 v_normal;
in vec3 v_frag_pos;

uniform sampler2D uTexture;
out vec4 FragColor;

void main()
{
    vec3 lightPos = vec3(5.0, 10.0, 7.0);
    vec3 lightColor = vec3(1.0, 1.0, 1.0);
    float ambientStrength = 0.25;
    float alphaThreshold = 0.05;

    vec4 texColor = texture(uTexture, v_texcoord) * v_color;
    vec3 ambient = ambientStrength * lightColor;

    // 2. Diffuse Component (The "Normal" workhorse)
    vec3 norm = normalize(v_normal);                 // Ensure normal is length 1
    vec3 lightDir = normalize(lightPos - v_frag_pos); // Direction pointing to the light
    
    // Dot product determines alignment. 1.0 = straight at light, 0.0 = perpendicular/shadowed
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;

    // 3. Combine Lighting Forces
    vec3 lightingResult = ambient + diffuse;

    FragColor = vec4(lightingResult * texColor.rgb, texColor.a);
}